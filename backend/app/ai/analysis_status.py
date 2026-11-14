"""Status honesto de uma análise (rodada de correções P0, homologação v1.0.2).

Antes, ``POST /analisar`` respondia sempre ``status:"concluida"`` — inclusive quando TODOS os
agentes falharam (sem chave, chave inválida, sem saldo). O usuário via "Análise concluída"
sem nenhuma IA ter rodado. Agora o status é calculado a partir das chamadas reais:

    concluida        todos os agentes executaram com sucesso (e há documento pronto, se há documentos)
    parcial          alguns agentes falharam OU nenhum documento estava pronto para análise
    falha            nenhum agente executou com sucesso (IA indisponível, orçamento, erro)
    em_processamento análise em curso (derivado do lock da operação; ver ``is_running``)

Função pura: não acessa banco nem rede (``is_running`` é a única exceção, só leitura).
"""
from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

STATUS_CONCLUIDA = "concluida"
STATUS_PARCIAL = "parcial"
STATUS_FALHA = "falha"
STATUS_EM_PROCESSAMENTO = "em_processamento"

ANALYSIS_STATUSES = (STATUS_CONCLUIDA, STATUS_PARCIAL, STATUS_FALHA, STATUS_EM_PROCESSAMENTO)

_OK = "CONCLUIDO"


def runs_for_status(orchestration: dict[str, Any]) -> list[dict[str, Any]]:
    """Chamadas dos agentes a considerar no status. Usa ``llm_runs`` (uma por agente, como o
    orquestrador real produz); se vier vazio, deriva de ``agent_results``: agente que não usou LLM
    conta como ``SEM_CHAVE`` (a IA não executou), nunca como sucesso."""
    runs = list(orchestration.get("llm_runs") or [])
    if runs:
        return runs
    derived: list[dict[str, Any]] = []
    for result in orchestration.get("agent_results") or []:
        call = result.get("llm_call") or {}
        status = call.get("status") or ("CONCLUIDO" if result.get("llm_used") else "SEM_CHAVE")
        derived.append({"agent": result.get("agent"), "status": status, "error_message": call.get("error_message")})
    return derived


def consolidate_status(runs: Iterable[dict[str, Any]], documents: dict[str, Any] | None = None) -> dict[str, Any]:
    """Consolida o status a partir das chamadas dos agentes e da prontidão dos documentos.

    ``runs``: dicts com ``agent`` e ``status`` (CONCLUIDO/ERRO/SEM_CHAVE/ORCAMENTO_EXCEDIDO/...).
    ``documents``: saída de ``property_documents_summary`` (total, prontos, nao_prontos).
    """
    run_list = list(runs)
    agents = [
        {
            "agente": r.get("agent") or "desconhecido",
            "status": r.get("status") or "ERRO",
            "erro": (r.get("error_message") or None),
        }
        for r in run_list
    ]
    total = len(agents)
    ok = sum(1 for a in agents if a["status"] == _OK)
    warnings: list[str] = []

    docs = documents or {"total": 0, "prontos": 0, "nao_prontos": []}
    if docs.get("total", 0) == 0:
        warnings.append("Nenhum documento enviado: a análise usa apenas os dados cadastrais.")
    else:
        for item in docs.get("nao_prontos", []):
            warnings.append(f"Documento '{item.get('nome')}' não está pronto para análise ({item.get('estado')}): {item.get('mensagem')}")

    if total == 0:
        code, status, message = "SEM_AGENTES", STATUS_FALHA, "Nenhum agente foi executado."
    elif ok == 0:
        statuses = {a["status"] for a in agents}
        if statuses == {"SEM_CHAVE"}:
            code, message = "IA_INDISPONIVEL", "A IA não está disponível (chave da OpenAI não configurada). Nenhum agente analisou o imóvel; o veredito usa só as regras determinísticas."
        elif "ORCAMENTO_EXCEDIDO" in statuses:
            code, message = "ORCAMENTO_EXCEDIDO", "O orçamento mensal de IA foi atingido. Nenhum agente foi executado."
        else:
            code, message = "FALHA_AGENTES", f"Todos os {total} agentes falharam. Consulte os erros por agente."
        status = STATUS_FALHA
    elif ok < total:
        code, status = "AGENTES_PARCIAIS", STATUS_PARCIAL
        failed = [a["agente"] for a in agents if a["status"] != _OK]
        message = f"{ok} de {total} agentes executaram. Falharam: {', '.join(failed)}."
    elif docs.get("total", 0) > 0 and docs.get("prontos", 0) == 0:
        code, status = "DOCUMENTOS_NAO_PRONTOS", STATUS_PARCIAL
        message = "Os agentes executaram, mas nenhum documento estava pronto para análise (sem texto/OCR). O resultado não se baseia em documentos."
    else:
        code, status = "OK", STATUS_CONCLUIDA
        message = f"{ok} de {total} agentes executaram com sucesso."
        if docs.get("nao_prontos"):
            message += " Há documentos não prontos; veja os avisos."

    return {
        "status": status,
        "codigo": code,
        "mensagem": message,
        "avisos": warnings,
        "agentes": agents,
        "agentes_ok": ok,
        "agentes_total": total,
        "ia_disponivel": ok > 0,
        "documentos_prontos": int(docs.get("prontos", 0)),
        "documentos_total": int(docs.get("total", 0)),
    }


def is_running(db: Session, property_id: int) -> bool:
    """Há uma análise em andamento para o imóvel? (lock advisory de ``/analisar`` retido por outra transação.)

    O lock é de transação (``pg_try_advisory_xact_lock``, chave ``analise:<id>``); enquanto a
    análise roda, ele aparece em ``pg_locks``. Somente leitura — não adquire o lock.
    """
    row = db.execute(
        text(
            "SELECT 1 FROM pg_locks WHERE locktype = 'advisory' AND granted AND pid <> pg_backend_pid() "
            "AND ((classid::bigint << 32) | (objid::bigint & 4294967295)) = hashtextextended(:k, 0) LIMIT 1"
        ),
        {"k": f"analise:{property_id}"},
    ).first()
    return row is not None
