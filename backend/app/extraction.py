from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator

from . import models
from .ai.gateway import BudgetExceeded, LLMCall, LLMGateway, build_gateway, sanitize_error
from .citations import ORIGEM_DOCUMENTO, FORTE, MODERADA, excerpt_in_text, normalize, value_in_text, value_window
from .config import settings
from .evidence import normalize_documentary_evidence
from .privacy_context import aliaser_for_property
from .rag.retriever import RetrieverFilters
from .rag.service import RAGService
from .services import persist_llm_runs, record_event, record_history

DocumentType = Literal["MATRICULA", "EDITAL"]

# Situação de cada campo e da extração como um todo (v1.0.4).
CAMPO_EXTRAIDO = "EXTRAIDO"            # valor com referência validada no texto do documento
CAMPO_NAO_ENCONTRADO = "NAO_ENCONTRADO"  # o modelo informou ausência (null): ausência legítima, não é erro
CAMPO_INCONCLUSIVO = "INCONCLUSIVO"    # o modelo preencheu, mas a referência não comprova o valor: descartado

EXTRACAO_CONCLUIDA = "CONCLUIDA"         # ao menos um campo extraído e comprovado
EXTRACAO_NAO_ENCONTRADA = "NAO_ENCONTRADO"  # nenhum dos campos consta do documento
EXTRACAO_INCONCLUSIVA = "INCONCLUSIVA"   # campos preenchidos, nenhum comprovado
EXTRACAO_SEM_TEXTO = "SEM_TEXTO"         # documento sem texto extraído: nenhuma chamada ao provider
EXTRACAO_ERRO = "ERRO"                   # falha do provider ou resposta malformada

# Campo de texto livre: o valor é um resumo; exige trecho literal, mas não que o valor apareça no texto.
FREE_TEXT_FIELDS = frozenset({"observations"})

_EXTRACTION_QUERY = {
    "MATRICULA": "matrícula número registro de imóveis oficial comarca proprietário certidão data",
    "EDITAL": "edital leilão data avaliação lance mínimo leiloeiro identificação",
}


class ExtractionReference(BaseModel):
    # A descrição vai no JSON schema enviado ao modelo: na 1ª execução v1.0.4 ele preencheu field="property_id"
    # (copiado do cabeçalho do trecho) em todas as referências.
    field: str = Field(description="Nome EXATO do campo extraído a que esta referência se refere (ex.: registration_number, notice_date, minimum_value). Nunca property_id, chunk_id ou document_id.")
    value: str = Field(min_length=1)
    chunk_id: int | None = None
    page: int | None = None
    section: str | None = None
    excerpt: str | None = None
    confidence: Literal["BAIXA", "MEDIA", "ALTA"] = "MEDIA"

    @field_validator("value", mode="before")
    @classmethod
    def _value_as_text(cls, value: Any) -> Any:
        # Function calling não é estrito: o modelo às vezes devolve o valor numérico (400000.0). O valor é só a
        # grafia citada; quem comprova o campo é o trecho conferido no documento (validate_fields_against_document).
        if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
            return format(Decimal(str(value)).normalize(), "f")
        return value

class RegistrationExtraction(BaseModel):
    registration_number: str | None = None
    registry_office: str | None = None
    comarca: str | None = None
    consultation_date: date | None = None
    holder: str | None = None
    observations: str | None = None
    references: list[ExtractionReference] = Field(default_factory=list)

class NoticeExtraction(BaseModel):
    identifier: str | None = None
    notice_date: date | None = None
    auction_stage: str | None = None
    appraisal_value: Decimal | None = None
    minimum_value: Decimal | None = None
    auction_date: date | None = None
    auctioneer: str | None = None
    observations: str | None = None
    references: list[ExtractionReference] = Field(default_factory=list)

class ExtractionResult:
    def __init__(self, document_type: str, version_id: int, call: LLMCall, output=None, chunks=None, field_status: dict[str, dict[str, Any]] | None = None, extraction_status: str | None = None, previous_calls: list[LLMCall] | None = None):
        self.document_type = document_type; self.document_version_id = version_id; self.call = call; self.output = output; self.chunks = chunks or []
        # Chamadas anteriores já cobradas (ex.: resposta truncada antes da única nova tentativa): entram em llm_runs.
        self.previous_calls = previous_calls or []
        self.field_status = field_status or {}
        self.extraction_status = extraction_status or (EXTRACAO_CONCLUIDA if call.status == "CONCLUIDO" and output is not None else EXTRACAO_ERRO)
    @property
    def success(self):
        # Ausência legítima (NAO_ENCONTRADO) é extração processada, não erro técnico; INCONCLUSIVA/ERRO não são.
        return self.call.status == "CONCLUIDO" and self.output is not None and self.extraction_status in (EXTRACAO_CONCLUIDA, EXTRACAO_NAO_ENCONTRADA)


_MINIMAL = (" RESPOSTA MÍNIMA (a tentativa anterior excedeu o limite de saída): observations = null; uma única referência "
            "por campo preenchido; excerpt com no máximo 120 caracteres.")


def _prompt(document_type: str, context: str, minimal: bool = False) -> list[dict[str, str]]:
    rules = (
        "Extraia somente fatos literalmente presentes no contexto, que contém APENAS este documento. Use null quando o "
        "campo não constar do documento: não deduza, não complete com dados de outro documento nem do cadastro. "
        "Nunca conclua validade, nulidade, risco, consolidação, evicção, regularidade, dívida ou ocupação. "
        "Para CADA campo preenchido crie uma referência: field = o nome exato do campo (ex.: notice_date), nunca property_id ou chunk_id; value = o valor exatamente como está "
        "escrito no documento; chunk_id = o número do cabeçalho [chunk_id=...] do trecho; excerpt = cópia LITERAL "
        "(até 200 caracteres) do trecho que contém o valor, sem resumir nem reescrever. Exatamente UMA referência por "
        "campo preenchido; observations com no máximo 200 caracteres. Datas nos campos em AAAA-MM-DD; "
        "valores monetários como número (ex.: 240000.00). Não informe página se o cabeçalho não trouxer page."
    )
    if minimal:
        rules += _MINIMAL
    return [{"role": "system", "content": f"Você é um extrator documental do Radar. Tipo: {document_type}. {rules}"}, {"role": "user", "content": json.dumps({"contexto": context}, ensure_ascii=False)}]


def _extraction_context(chunks: list[dict[str, Any]]) -> str:
    parts = []
    for chunk in chunks:
        page = f" page={chunk['page']}" if chunk.get("page") is not None else ""
        parts.append(f"[chunk_id={chunk.get('chunk_id')}{page}]\n{chunk.get('content') or ''}")
    return "\n\n".join(parts)


def _field_key(name: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", normalize(name)).strip("_")


def validate_extraction_references(output: RegistrationExtraction | NoticeExtraction) -> None:
    """Estrutural: todo campo preenchido tem uma referência com o mesmo ``field``. A validação contra o TEXTO do
    documento é feita por ``validate_fields_against_document`` (chamada em ``extract_document``)."""
    referenced = {reference.field for reference in output.references}
    for field_name in output.model_fields:
        if field_name == "references": continue
        if getattr(output, field_name) is not None and field_name not in referenced:
            raise ValueError(f"Campo extraído sem referência correspondente: {field_name}")


def _check_reference(field_name: str, value: Any, reference: ExtractionReference, chunks_by_id: dict[int, dict[str, Any]], pages: set[int]) -> tuple[ExtractionReference | None, str]:
    """Confere UMA referência contra o conteúdo extraído do documento; devolve a referência corrigida a partir da
    fonte (chunk, página e seção reais) ou o motivo da rejeição."""
    if reference.chunk_id is not None and reference.chunk_id not in chunks_by_id:
        return None, "a referência aponta para um trecho que não pertence a este documento"
    if reference.page is not None and pages and reference.page not in pages:
        return None, f"página {reference.page} não existe no documento"
    candidates = [chunks_by_id[reference.chunk_id]] if reference.chunk_id is not None else list(chunks_by_id.values())
    excerpt = (reference.excerpt or "").strip()
    hit = None
    if excerpt:
        hit = next((chunk for chunk in candidates if excerpt_in_text(excerpt, chunk.get("content"))), None)
        if hit is None and reference.chunk_id is not None:
            # chunk_id errado com trecho certo (execução real v1.0.4: data do edital no 2º trecho citada como 1º):
            # procura nos demais trechos DESTE documento; o ponteiro é corrigido a partir da fonte.
            hit = next((chunk for chunk in chunks_by_id.values() if excerpt_in_text(excerpt, chunk.get("content"))), None)
        if hit is None:
            return None, "o trecho citado não aparece no documento"
        if field_name not in FREE_TEXT_FIELDS and not value_in_text(value, excerpt):
            return None, "o trecho citado não contém o valor extraído"
    else:
        if field_name in FREE_TEXT_FIELDS:
            return None, "observação sem trecho literal do documento"
        hit = next((chunk for chunk in candidates if value_in_text(value, chunk.get("content"))), None)
        if hit is None:
            return None, "o valor extraído não aparece no documento"
        excerpt = value_window(value, hit.get("content"))
    fixed = reference.model_copy(update={"chunk_id": hit.get("chunk_id"), "page": hit.get("page"), "section": hit.get("section") or reference.section, "excerpt": excerpt[:600]})
    return fixed, ""


def validate_fields_against_document(output: RegistrationExtraction | NoticeExtraction, chunks: list[dict[str, Any]]) -> tuple[RegistrationExtraction | NoticeExtraction, dict[str, dict[str, Any]]]:
    """Valida cada campo preenchido contra o texto efetivamente extraído do documento.

    Campo sem referência válida é DESCARTADO (vira None, situação INCONCLUSIVO, com o motivo) em vez de derrubar a
    extração inteira; campo null é NAO_ENCONTRADO (ausência legítima). Só referências validadas são mantidas.
    """
    chunks_by_id = {chunk["chunk_id"]: chunk for chunk in chunks if chunk.get("chunk_id") is not None}
    pages = {chunk["page"] for chunk in chunks if chunk.get("page") is not None}
    known = {name for name in output.model_fields if name != "references"}
    by_field: dict[str, list[ExtractionReference]] = {}
    orphans: list[ExtractionReference] = []   # field com nome que não é campo do schema (ex.: "property_id")
    for reference in output.references:
        key = _field_key(reference.field)
        if key in known:
            by_field.setdefault(key, []).append(reference)
        else:
            orphans.append(reference)
    updates: dict[str, Any] = {}
    kept: list[ExtractionReference] = []
    status: dict[str, dict[str, Any]] = {}
    for field_name in output.model_fields:
        if field_name == "references": continue
        value = getattr(output, field_name)
        if value is None:
            status[field_name] = {"status": CAMPO_NAO_ENCONTRADO}
            continue
        reason = "campo preenchido sem referência ao documento"
        accepted = None
        for reference in by_field.get(field_name, []):
            accepted, reason = _check_reference(field_name, value, reference, chunks_by_id, pages)
            if accepted is not None:
                break
        reassigned = False
        if accepted is None and field_name not in FREE_TEXT_FIELDS:
            # Referência com nome de campo errado só vale se o TRECHO literal (conferido no documento) contém o valor.
            for reference in orphans:
                if reference.excerpt and value_in_text(value, reference.excerpt):
                    candidate = reference.model_copy(update={"field": field_name, "value": str(value)})
                    accepted, _reason = _check_reference(field_name, value, candidate, chunks_by_id, pages)
                    if accepted is not None:
                        reassigned = True
                        break
        if accepted is None:
            updates[field_name] = None
            status[field_name] = {"status": CAMPO_INCONCLUSIVO, "motivo": reason}
            continue
        if accepted.field != field_name:
            accepted = accepted.model_copy(update={"field": field_name})
        kept.append(accepted)
        status[field_name] = {"status": CAMPO_EXTRAIDO, "chunk_id": accepted.chunk_id, "page": accepted.page}
        if reassigned:
            status[field_name]["referencia"] = "trecho do documento reatribuído ao campo (o modelo informou outro nome de campo)"
    updates["references"] = kept
    return output.model_copy(update=updates), status


def _overall_status(field_status: dict[str, dict[str, Any]]) -> str:
    states = [item["status"] for item in field_status.values()]
    if CAMPO_EXTRAIDO in states:
        return EXTRACAO_CONCLUIDA
    if CAMPO_INCONCLUSIVO in states:
        return EXTRACAO_INCONCLUSIVA
    return EXTRACAO_NAO_ENCONTRADA


def extract_document(db, property_id: int, document_version_id: int, document_type: str, gateway_override: LLMGateway | None = None) -> ExtractionResult:
    version = db.get(models.DocumentVersion, document_version_id)
    if not version or version.document.property_id != property_id: raise ValueError("DocumentVersion não pertence ao imóvel")
    document_type = document_type.upper()
    schema = RegistrationExtraction if document_type == "MATRICULA" else NoticeExtraction if document_type == "EDITAL" else None
    if schema is None: raise ValueError("Tipo de documento não suportado")
    # Contexto = trechos DESTE documento (filtro por versão). ``broad``: sem busca vetorial, a consulta textual
    # literal ("matricula") podia não casar nenhum trecho e a extração rodava com contexto vazio; agora usa
    # termos típicos do tipo e, sem correspondência, os primeiros trechos do próprio documento.
    retrieval = RAGService(db).retrieve_context(_EXTRACTION_QUERY[document_type], property_id, filters=RetrieverFilters(property_id=property_id, document_id=version.document_id, document_version=version.version), broad=True)
    if not any(str(chunk.get("content") or "").strip() for chunk in retrieval.chunks):
        # Sem texto extraído não há o que citar: não gasta uma chamada que seria necessariamente rejeitada.
        call = LLMCall(provider=settings.llm_provider, model=settings.llm_model, status="IGNORADO", error_type="SemTexto", error_message="Documento sem texto extraído; extração não executada (nenhuma chamada ao provider)")
        return ExtractionResult(document_type, document_version_id, call, None, retrieval.chunks, {}, EXTRACAO_SEM_TEXTO)
    if gateway_override is not None: gateway = gateway_override
    else:
        try: gateway = build_gateway()
        except RuntimeError as exc:
            # Orçamento atingido não pode ser mascarado como "sem chave" (e o modelo real deve constar do registro).
            status = "ORCAMENTO_EXCEDIDO" if isinstance(exc, BudgetExceeded) else "SEM_CHAVE"
            return ExtractionResult(document_type, document_version_id, LLMCall.unavailable(settings.llm_provider, settings.llm_model, str(exc), status=status), None, retrieval.chunks, {}, status)
    # Contexto só com o identificador do trecho: os metadados do RAG (property_id, scores...) não são do documento
    # e confundiam o modelo (referências com field="property_id").
    context = _extraction_context(retrieval.chunks)
    # Pseudonimização de pessoas físicas conhecidas antes do envio; a resposta é restaurada localmente.
    aliaser = aliaser_for_property(db, property_id)
    aliaser.learn_from_text(context)
    call = gateway.structured_chat(schema, _prompt(document_type, aliaser.apply(context)))
    previous: list[LLMCall] = []
    if call.status != "CONCLUIDO" and call.error_category == "LIMITE_DE_SAIDA":
        # Resposta truncada por LLM_MAX_OUTPUT_TOKENS (cobrada e descartada): UMA única nova tentativa, pedindo resposta
        # mínima. Sem laço: se falhar de novo, a extração termina em ERRO e as duas chamadas ficam registradas.
        previous.append(call)
        call = gateway.structured_chat(schema, _prompt(document_type, aliaser.apply(context), minimal=True))

    def done(output=None, field_status=None, overall=EXTRACAO_ERRO):
        return ExtractionResult(document_type, document_version_id, call, output, retrieval.chunks, field_status or {}, overall, previous)

    if call.status != "CONCLUIDO": return done()
    try:
        output = call.content if isinstance(call.content, schema) else schema.model_validate(call.content)
        output = schema.model_validate(aliaser.restore_obj(output.model_dump(mode="python")))
    except Exception as exc:
        call.status = "ERRO"; call.error_type = type(exc).__name__; call.error_message = sanitize_error(str(exc)); return done()
    output, field_status = validate_fields_against_document(output, retrieval.chunks)
    overall = _overall_status(field_status)
    if overall == EXTRACAO_INCONCLUSIVA:
        # A chamada foi feita (e cobrada: tokens ficam no llm_run), mas nada foi comprovado: não é extração concluída.
        rejected = ", ".join(f"{name} ({info.get('motivo')})" for name, info in field_status.items() if info["status"] == CAMPO_INCONCLUSIVO)
        call.status = "ERRO"; call.error_type = "ExtracaoInconclusiva"; call.error_message = sanitize_error(f"Extração inconclusiva: nenhum campo com referência válida no documento: {rejected}")
        return done(None, field_status, overall)
    return done(output, field_status, overall)


def persist_extraction(db, prop: models.Property, result: ExtractionResult):
    if not result.success: raise ValueError("Não é possível persistir uma extração inválida")
    validate_extraction_references(result.output)
    version = db.get(models.DocumentVersion, result.document_version_id); output = result.output
    if result.document_type == "MATRICULA":
        item = models.PropertyRegistration(property_id=prop.id, registration_number=output.registration_number, registry_office=output.registry_office, comarca=output.comarca, consultation_date=output.consultation_date, holder=output.holder, observations=output.observations, document_version_id=version.id)
        target_type = "PropertyRegistration"; event_type = "MATRICULA_EXTRAIDA"; domains = ["juridico", "checklist"]
    else:
        item = models.AuctionNotice(property_id=prop.id, identifier=output.identifier, notice_date=output.notice_date, auction_stage=output.auction_stage, appraisal_value=output.appraisal_value, minimum_value=output.minimum_value, auction_date=output.auction_date, auctioneer=output.auctioneer, observations=output.observations, document_version_id=version.id)
        target_type = "AuctionNotice"; event_type = "EDITAL_EXTRAIDO"; domains = ["documental", "juridico", "financeiro", "checklist"]
    db.add(item); db.flush(); evidence_ids = []
    for reference in output.references:
        # Referência já conferida contra o texto do documento: trecho literal da fonte.
        strength = FORTE if reference.excerpt else MODERADA
        info = (getattr(result, "field_status", {}) or {}).get(reference.field) or {}
        if info.get("referencia"):
            strength = MODERADA   # campo associado pelo servidor a partir do trecho: exige leitura humana
        typed = getattr(output, reference.field, None)
        fact_value = typed if typed is not None and reference.field not in FREE_TEXT_FIELDS else reference.value
        evidence = normalize_documentary_evidence(db=db, property_id=prop.id, document_version_id=version.id, chunk_id=reference.chunk_id, category=result.document_type, fact=f"{reference.field}: {fact_value}", confidence=reference.confidence, page=reference.page, section=reference.section, source_excerpt=reference.excerpt, target_type=target_type, target_id=item.id, origin=ORIGEM_DOCUMENTO, strength=strength, agent="extracao_documental")
        evidence_ids.append(evidence.id)
    item.evidence_id = evidence_ids[0] if evidence_ids else None
    payload = {"document_version_id": version.id, "record_id": item.id, "evidence_ids": evidence_ids, "campos": getattr(result, "field_status", {})}
    event = record_event(db, prop, event_type, target_type, item.id, payload, domains); record_history(db, prop, target_type, item.id, "CREATE", None, payload, event.id, item.evidence_id)
    return item, evidence_ids
