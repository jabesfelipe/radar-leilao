import json
from dataclasses import dataclass, field
from typing import Any
from sqlalchemy.orm import Session
from .. import models
from ..config import settings
from ..market import calculate_market
from ..services import build_finance, latest_execution, serialize
from .contracts import AgentResponse
from ..privacy import minimize_party
from ..privacy_context import aliaser_for_property
from .budget import unavailable_reason
from .gateway import LLMCall, LLMGateway, sanitize_error
from .prompts import ANALYSIS_SYSTEM_PROMPT, DOCUMENT_REVIEW_POINTS, SOURCE_RULES

@dataclass
class AgentResult:
    agent: str
    facts: list[dict[str, Any]]
    evidence_ids: list[int]
    interpretation: str = ""
    pending: list[str] = field(default_factory=list)
    llm_used: bool = False
    model: str | None = None
    llm_call: LLMCall | None = None
    retrieved_chunk_ids: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"agent": self.agent, "facts": self.facts, "evidence_ids": self.evidence_ids, "interpretation": self.interpretation, "pending": self.pending, "llm_used": self.llm_used, "model": self.model, "llm_call": self.llm_call.to_dict() if self.llm_call else None, "retrieved_chunk_ids": self.retrieved_chunk_ids}

class RadarAgent:
    name = "base"
    focus = "análise do imóvel"

    def __init__(self, db: Session, gateway: LLMGateway | None = None):
        self.db = db
        self.gateway = gateway

    _aliaser = None  # NameAliaser do imóvel em análise (definido em _run_llm)
    unavailable_override: tuple[str, str] | None = None  # (status, mensagem) imposto pelo orçamento da análise

    def _party(self, name: str | None, role: str) -> str | None:
        """Parte de processo: apelido consistente quando há aliaser; senão, pseudonimização simples."""
        if self._aliaser is not None:
            return self._aliaser.alias_for(name, role)
        return minimize_party(name, role)

    def _property_snapshot(self, property_id: int) -> dict[str, Any]:
        prop = self.db.get(models.Property, property_id)
        if not prop: return {}
        return {"id": prop.id, "titulo": prop.title, "endereco": prop.address, "cidade": prop.city, "estado": prop.state, "tipo": prop.property_type, "area_m2": serialize(prop.area_m2), "quartos": prop.bedrooms, "processos": [{"numero": p.number, "assunto": p.subject, "status": p.status, "impacto": p.impact} for p in prop.processes], "comparaveis": [{"tipo": c.kind, "preco": serialize(c.price), "aluguel": serialize(c.rent), "area_m2": serialize(c.area_m2), "fonte": c.source} for c in prop.comparables], "documentos": [{"nome": d.name, "tipo": d.document_type, "status": d.status} for d in prop.documents]}

    def _run_llm(self, property_id: int, context: str, instructions: str, retrieved_chunk_ids: list[int], extra: dict[str, Any] | None = None) -> AgentResult:
        if not self.gateway:
            status, reason = self.unavailable_override or unavailable_reason(self.db)
            call = LLMCall.unavailable(settings.llm_provider, settings.llm_model, reason, status=status)
            pending = "Configurar OPENAI_API_KEY para executar a análise interpretativa" if status == "SEM_CHAVE" else "Aguardar o próximo ciclo de orçamento ou ajustar LLM_BUDGET_USD_MONTH"
            return AgentResult(self.name, [{"kind": "ausencia", "statement": call.error_message, "confidence": "BAIXA", "chunk_ids": []}], [], "LLM não configurada" if status == "SEM_CHAVE" else "IA indisponível", [pending], False, call.model, call, retrieved_chunk_ids)
        # Pseudonimização de PESSOAS FÍSICAS conhecidas (titular, partes, ocupantes + nomes após rótulos
        # jurídicos no texto): o LLM vê papéis ("[TITULAR]"), nunca o nome; as respostas são restauradas
        # localmente antes de gravar. O aliaser é só do imóvel analisado (ver privacy_context.py).
        self._aliaser = aliaser_for_property(self.db, property_id)
        self._aliaser.learn_from_text(context)
        payload = {"imovel": self._property_snapshot(property_id), "contexto_rag": context, **(extra or {})}
        user_content = self._aliaser.apply(json.dumps(payload, ensure_ascii=False, default=str))
        messages = [{"role": "system", "content": ANALYSIS_SYSTEM_PROMPT + "\nVocê é o agente " + self.name + ". " + instructions + "\n" + SOURCE_RULES}, {"role": "user", "content": user_content}]
        call = self.gateway.structured_chat(AgentResponse, messages)
        if call.status != "CONCLUIDO":
            return AgentResult(self.name, [], [], "", [call.error_message or "Falha na execução do agente"], False, call.model, call, retrieved_chunk_ids)
        try:
            response = call.content
            parsed = response if isinstance(response, AgentResponse) else AgentResponse.model_validate(response)
            facts = self._aliaser.restore_obj([finding.model_dump() for finding in parsed.findings])
            parsed.summary = self._aliaser.restore(parsed.summary)
            parsed.pending = self._aliaser.restore_obj(parsed.pending)
            evidence_ids = [chunk_id for finding in facts for chunk_id in finding.get("chunk_ids", [])]
        except Exception as exc:
            call.status = "ERRO"; call.error_type = type(exc).__name__; call.error_message = sanitize_error(str(exc))
            return AgentResult(self.name, [], [], "", ["Resposta estruturada inválida"], False, call.model, call, retrieved_chunk_ids)
        return AgentResult(self.name, facts, sorted(set(evidence_ids)), parsed.summary, parsed.pending, True, call.model, call, retrieved_chunk_ids)

    def run(self, property_id: int, context: str = "", retrieved_chunk_ids: list[int] | None = None) -> AgentResult:
        raise NotImplementedError

class DocumentAgent(RadarAgent):
    name = "documental"
    def run(self, property_id: int, context: str = "", retrieved_chunk_ids: list[int] | None = None) -> AgentResult:
        return self._run_llm(property_id, context, "Extraia somente fatos documentais, ausência de informação e interpretações documentais estritamente suportadas pelo trecho. Não produza risco, avaliação de compra, veredito, conclusão jurídica, validade, nulidade ou regularidade. " + DOCUMENT_REVIEW_POINTS, retrieved_chunk_ids or [])

class LegalAgent(RadarAgent):
    name = "juridico"

    def _property_snapshot(self, property_id: int) -> dict[str, Any]:
        snapshot = super()._property_snapshot(property_id)
        prop = self.db.get(models.Property, property_id)
        if not prop:
            return snapshot
        snapshot["processos"] = [
            {
                "numero": process.number,
                "tribunal": process.court,
                "comarca": process.comarca,
                "natureza": process.nature,
                "assunto": process.subject,
                "status": process.status,
                # Minimização: pessoa física vira "[PARTE ATIVA]"/"[PARTE PASSIVA]"; empresas,
                # bancos, condomínios e entes públicos permanecem (necessários à análise).
                "polo_ativo": self._party(process.polo_active, "PARTE ATIVA"),
                "polo_passivo": self._party(process.polo_passive, "PARTE PASSIVA"),
                "data_distribuicao": serialize(process.distribution_date),
                "observacoes": process.observations,
                "fonte": process.source,
                "consultado_em": serialize(process.consulted_at),
                "impacto_cadastrado": process.impact,
                "movimentacoes": [
                    {
                        "data": serialize(movement.movement_date),
                        "descricao": movement.description,
                        "fonte": movement.source,
                    }
                    for movement in process.movements
                ],
            }
            for process in prop.processes
        ]
        return snapshot

    def run(self, property_id: int, context: str = "", retrieved_chunk_ids: list[int] | None = None) -> AgentResult:
        instructions = (
            "Analise exclusivamente fatos jurídicos e documentais do imóvel, incluindo matrícula, edital, "
            "processos, movimentações, consolidação, registros e averbações. Identifique fatos relevantes e "
            "relacione-os a checklist_key e checklist_state somente quando a regra existente estiver explicitamente "
            "suportada. Diferencie fato, interpretação, hipótese e ausência de informação. Use somente o contexto "
            "RAG e o snapshot cadastrado; informe chunk_ids, página, seção e trecho para cada conclusão baseada "
            "em documento. Não invente fatos, não afirme certeza jurídica sem base, não declare validade ou "
            "nulidade automaticamente, não emita veredito de compra, não calcule preço e não crie risco final. "
            "Quando houver dúvida, registre como hipótese ou ausência e preserve a evidência; a análise não substitui "
            "decisão jurídica profissional."
        )
        return self._run_llm(property_id, context, instructions, retrieved_chunk_ids or [])

class FinancialAgent(RadarAgent):
    name = "financeiro"

    def run(
        self,
        property_id: int,
        context: str = "",
        retrieved_chunk_ids: list[int] | None = None,
        deterministic_finance: dict[str, Any] | None = None,
    ) -> AgentResult:
        prop = self.db.get(models.Property, property_id)
        finance = deterministic_finance if deterministic_finance is not None else (serialize(build_finance(prop)) if prop else {})
        instructions = (
            "Interprete exclusivamente o resultado financeiro determinístico fornecido em "
            "financeiro_deterministico. Explique custo total, desconto, margem, yield e dados ausentes "
            "quando disponíveis; diferencie fato calculado, interpretação, hipótese e ausência. "
            "Não recalcule. Não altere qualquer número do Finance Engine. Não invente custos, "
            "dívidas, aluguel, valor de mercado ou preço máximo; não crie score, risco final ou veredito "
            "de compra. O preço máximo pode permanecer pendente quando o motor informar essa pendência. "
            "Se mencionar dado financeiro documental, informe chunk_ids, page, section e evidence_excerpt. "
            "Quando faltarem dados, registre ausência ou pendência sem inferir valores."
        )
        return self._run_llm(property_id, context, instructions, retrieved_chunk_ids or [], {"financeiro_deterministico": finance})

class MarketAgent(RadarAgent):
    name = "mercado"

    def run(
        self,
        property_id: int,
        context: str = "",
        retrieved_chunk_ids: list[int] | None = None,
        deterministic_market: dict[str, Any] | None = None,
    ) -> AgentResult:
        prop = self.db.get(models.Property, property_id)
        if deterministic_market is None:
            comparables = [{"kind": item.kind, "price": item.price, "rent": item.rent, "area_m2": item.area_m2} for item in (prop.comparables if prop else [])]
            market = serialize(calculate_market(comparables))
        else:
            market = deterministic_market
        instructions = (
            "Interprete exclusivamente o resumo determinístico fornecido em mercado_deterministico. "
            "Explique quantidade de comparáveis, preços médios/medianos, preço por m², aluguéis "
            "médios/medianos e aluguel por m² quando disponíveis. Diferencie fatos calculados, "
            "interpretações, hipóteses e ausências. Não recalcule. Não altere nenhum indicador; não "
            "invente comparáveis, preços ou aluguéis; não crie valuation, valor de mercado, score de "
            "liquidez, risco final ou veredito de compra. Não afirme liquidez como fato sem evidência. "
            "Quando faltarem comparáveis ou área, registre ausência ou pendência sem inferir. Se usar "
            "informação documental, informe chunk_ids, page, section e evidence_excerpt."
        )
        return self._run_llm(property_id, context, instructions, retrieved_chunk_ids or [], {"mercado_deterministico": market})

class ChecklistAgent(RadarAgent):
    name = "checklist"

    def run(
        self,
        property_id: int,
        context: str = "",
        retrieved_chunk_ids: list[int] | None = None,
        checklist_items: list[dict[str, Any]] | None = None,
    ) -> AgentResult:
        if checklist_items is None:
            prop = self.db.get(models.Property, property_id)
            execution = latest_execution(prop) if prop else None
            checklist_items = [
                {
                    "canonical_key": result.item.canonical_key,
                    "question": result.item.question,
                    "category": result.item.category,
                    "active": result.item.active,
                    "applicable": result.applicable,
                    "item_version": result.item_version,
                }
                for result in (execution.results if execution else [])
            ]
        instructions = (
            "Relacione somente evidências às regras existentes do Checklist Mestre fornecidas em "
            "checklist_mestre. Use exclusivamente canonical_key presentes nessa lista e os estados "
            "PENDENTE, EM_ANALISE, CONFIRMADO, RISCO_IDENTIFICADO, ATENCAO, NAO_IDENTIFICADO ou "
            "NAO_APLICAVEL. Não crie regras, canonical_key, perguntas ou estados. Diferencie fato, "
            "interpretação, hipótese e ausência. Só indique NAO_APLICAVEL quando houver evidência "
            "suficiente; caso contrário mantenha a pendência. Toda resposta baseada em documento deve "
            "informar chunk_ids, page, section e evidence_excerpt. Sem evidência suficiente, registre "
            "ausência ou pendência sem inventar resultado. "
            "Significado dos estados quando HÁ trecho do documento que responde à PERGUNTA do item: "
            "CONFIRMADO = a resposta à pergunta é SIM (não basta o documento conter os valores citados na pergunta); "
            "NAO_IDENTIFICADO = a resposta à pergunta é NÃO; RISCO_IDENTIFICADO = o documento mostra um risco (ônus, "
            "penhora, indisponibilidade, ação); ATENCAO = ponto que exige cuidado ou custo (ocupação, débitos por conta do "
            "arrematante). Use PENDENTE apenas quando o contexto não responde à pergunta; nesse caso use kind=ausencia sem "
            "chunk_ids. Não avalie itens calculados pelo Radar (LANCE_MENOR_50_AVALIACAO, PRAZO_DOIS_ANOS, COMPARAVEIS_SUFFICIENTES)."
        )
        return self._run_llm(
            property_id,
            context,
            instructions,
            retrieved_chunk_ids or [],
            {"checklist_mestre": checklist_items or []},
        )

class _RunBudget:
    """Acumula o custo da análise em curso e decide se o próximo agente pode chamar o provider."""

    def __init__(self, db: Session):
        from decimal import Decimal
        from .budget import month_status
        self.db = db
        self.spent = Decimal("0")
        status = month_status(db) if settings.llm_budget_usd_month is not None else {"gasto_usd": 0.0}
        self.month_base = Decimal(str(status.get("gasto_usd") or 0))

    def add(self, call: LLMCall | None) -> None:
        from .costs import calculate_cost, resolve_pricing
        if call is None or call.input_tokens is None or call.output_tokens is None:
            return
        cost = calculate_cost(call.input_tokens, call.output_tokens, resolve_pricing(self.db, call.provider, call.model))["total_cost"]
        if cost is not None:
            self.spent += cost

    def blocked_reason(self) -> str | None:
        if settings.llm_budget_usd_per_analysis is not None and float(self.spent) >= settings.llm_budget_usd_per_analysis:
            return "Teto de custo desta análise atingido; os agentes restantes não foram executados"
        if settings.llm_budget_usd_month is not None and float(self.month_base + self.spent) >= settings.llm_budget_usd_month:
            return "Orçamento mensal de IA atingido durante a análise; os agentes restantes não foram executados"
        return None


class Supervisor:
    def __init__(self, db: Session, gateway: LLMGateway | None = None):
        self.db = db
        self.gateway = gateway

    def run(
        self,
        property_id: int,
        domains: list[str],
        context: str = "",
        retrieved_chunk_ids: list[int] | None = None,
        checklist_context: str | None = None,
        checklist_chunk_ids: list[int] | None = None,
    ) -> list[AgentResult]:
        available = {a.name: a for a in [DocumentAgent(self.db, self.gateway), LegalAgent(self.db, self.gateway), FinancialAgent(self.db, self.gateway), MarketAgent(self.db, self.gateway), ChecklistAgent(self.db, self.gateway)]}
        results: list[AgentResult] = []
        # Orçamento DURANTE a análise: as chamadas só entram em llm_runs ao final, então o gasto da própria
        # análise é acumulado aqui (tokens reais x llm_pricing) e comparado ao teto mensal e ao teto por análise.
        guard = _RunBudget(self.db) if self.gateway is not None and (settings.llm_budget_usd_month is not None or settings.llm_budget_usd_per_analysis is not None) else None
        for name in domains:
            agent = available.get(name)
            if not agent:
                continue
            if guard is not None:
                blocked = guard.blocked_reason()
                if blocked:
                    agent.gateway = None
                    agent.unavailable_override = ("ORCAMENTO_EXCEDIDO", blocked)
            try:
                # O ChecklistAgent recebe o contexto direcionado (RAG por item) quando
                # disponível; os demais agentes seguem com o contexto genérico. Isso
                # não altera o contrato dos outros agentes.
                if name == "checklist" and checklist_context is not None:
                    results.append(agent.run(property_id, checklist_context, checklist_chunk_ids or retrieved_chunk_ids))
                else:
                    results.append(agent.run(property_id, context, retrieved_chunk_ids))
                if guard is not None and results:
                    guard.add(results[-1].llm_call)
            except Exception as exc:
                call = LLMCall(provider=self.gateway.provider_name if self.gateway else settings.llm_provider, model=self.gateway.model if self.gateway else settings.llm_model, status="ERRO", error_type=type(exc).__name__, error_message=sanitize_error(str(exc)))
                results.append(AgentResult(name, [], [], "", [call.error_message or "Falha no agente"], False, call.model, call, retrieved_chunk_ids or []))
        return results
