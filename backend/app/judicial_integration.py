"""Integração Radar → Judicial API (TASK FINAL — Entrega 3).

Consome a Judicial API por HTTP (via ``JudicialApiClient``) e persiste o resultado
jurídico no contexto do imóvel, reutilizando as entidades existentes do Radar:

- cada processo retornado vira/atualiza um ``LegalProcess`` (com ``ProcessMovement``),
  marcado com ``source="Judicial API (DataJud)"`` e ``consulted_at``;
- cada sinal jurídico vira uma ``Evidence`` (``category="JURIDICO"``) que preserva a
  distinção processo × imóvel — evidência processual NUNCA é tratada como gravame
  confirmado na matrícula (SPEC §35, §39; item 9 da task);
- um ``DomainEvent`` "CONSULTA_JUDICIAL_REALIZADA" registra a execução para
  auditoria/histórico e alimenta a reanálise incremental.

O Radar NÃO duplica provider/orchestrator/signals: tudo isso vive na Judicial API.
Este módulo apenas orquestra a chamada HTTP e a persistência no domínio do Radar.

Idempotência: um processo já cadastrado para o imóvel (mesmo ``number``) é
atualizado no lugar (não duplica); movimentos são substituídos pela lista corrente.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .judicial_client import (
    JudicialApiClient,
    JudicialApiError,
    JudicialApiUnavailable,
    JudicialSearchOutcome,
)
from .services import record_event, record_history

# Origem canônica dos processos/evidências consultados pela Judicial API.
JUDICIAL_SOURCE = "Judicial API (DataJud)"

# Mapeia a confiança numérica (0..1) do sinal para o vocabulário do Radar.
def _confidence_label(value: float | None) -> str:
    v = value if isinstance(value, (int, float)) else 0.5
    if v >= 0.75:
        return "ALTA"
    if v >= 0.4:
        return "MEDIA"
    return "BAIXA"


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    # Aceita datas ISO e datetimes ISO; extrai apenas a parte de data.
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(text[: len(fmt) + 6], fmt).date()
        except (ValueError, TypeError):
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return None


@dataclass
class JudicialConsultResult:
    """Resumo do que foi consultado/persistido, para a resposta da API."""

    status: str
    search_id: str | None
    processes_created: int = 0
    processes_updated: int = 0
    signals_created: int = 0
    sources: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reanalyze: dict[str, Any] = field(default_factory=dict)
    available: bool = True
    message: str | None = None


class JudicialIntegrationService:
    """Orquestra a consulta à Judicial API e a persistência no domínio do Radar."""

    def __init__(self, db: Session, client: JudicialApiClient | None = None) -> None:
        self.db = db
        self.client = client or JudicialApiClient()

    def consult_for_property(self, prop: models.Property, criteria: dict[str, Any]) -> JudicialConsultResult:
        """Consulta a Judicial API e persiste processos/sinais para o imóvel.

        Levanta ``JudicialApiUnavailable``/``JudicialApiError`` para o chamador
        decidir a degradação — não persiste nada em caso de indisponibilidade.
        """
        outcome = self.client.search(criteria)
        return self._persist(prop, outcome)

    def _persist(self, prop: models.Property, outcome: JudicialSearchOutcome) -> JudicialConsultResult:
        result = JudicialConsultResult(
            status=outcome.status,
            search_id=outcome.search_id,
            sources=outcome.sources,
            warnings=outcome.warnings,
            reanalyze=outcome.reanalyze,
        )
        # Índice dos processos já cadastrados do imóvel (por número normalizado).
        existing = {
            _digits(p.number): p
            for p in self.db.scalars(
                select(models.LegalProcess).where(models.LegalProcess.property_id == prop.id)
            ).all()
        }
        now = datetime.now(timezone.utc)
        affected_ids: list[int] = []
        for proc in outcome.processes:
            number = str(proc.get("process_number") or "").strip()
            if not number:
                continue
            key = _digits(number)
            record = existing.get(key)
            polos = _split_parties(proc.get("parties", []))
            if record is None:
                record = models.LegalProcess(property_id=prop.id, number=number)
                self.db.add(record)
                result.processes_created += 1
            else:
                result.processes_updated += 1
            record.court = proc.get("tribunal") or record.court
            record.subject = _first_subject(proc.get("subjects", [])) or record.subject
            record.nature = proc.get("class_name") or record.nature
            record.polo_active = polos["ativo"] or record.polo_active
            record.polo_passive = polos["passivo"] or record.polo_passive
            record.source = JUDICIAL_SOURCE
            record.consulted_at = now
            self.db.flush()
            affected_ids.append(record.id)
            self._replace_movements(record, proc.get("movements", []))

        for signal in outcome.signals:
            self._persist_signal(prop, signal)
            result.signals_created += 1

        payload = {
            "search_id": outcome.search_id,
            "status": outcome.status,
            "processos": len(outcome.processes),
            "sinais": len(outcome.signals),
            "fontes": [s.get("tribunal") for s in outcome.sources],
        }
        event = record_event(
            self.db, prop, "CONSULTA_JUDICIAL_REALIZADA", "LegalProcess",
            affected_ids[0] if affected_ids else None, payload,
            ["juridico", "checklist"],
        )
        record_history(self.db, prop, "LegalProcess", affected_ids[0] if affected_ids else 0, "CONSULT", None, payload, event.id)
        return result

    def _replace_movements(self, process: models.LegalProcess, movements: list[dict[str, Any]]) -> None:
        # Substitui os movimentos oriundos da Judicial API pela lista corrente,
        # preservando eventuais movimentos de cadastro manual (fonte diferente).
        for existing in list(process.movements):
            if existing.source == JUDICIAL_SOURCE:
                self.db.delete(existing)
        self.db.flush()
        for mov in movements:
            description = (mov.get("description") or mov.get("complement") or "").strip()
            if not description:
                continue
            self.db.add(
                models.ProcessMovement(
                    process_id=process.id,
                    movement_date=_parse_iso_date(mov.get("movement_date")),
                    description=description,
                    source=JUDICIAL_SOURCE,
                )
            )

    def _persist_signal(self, prop: models.Property, signal: dict[str, Any]) -> None:
        code = signal.get("signal_code", "SINAL")
        tribunal = signal.get("tribunal")
        number = signal.get("process_number")
        origem = " ".join(part for part in [tribunal, number] if part)
        interpretation = (
            "Evidência processual detectada pela Judicial API. NÃO confirma, por si só, "
            "gravame sobre o imóvel: a correlação com a matrícula exige validação registral/documental."
        )
        evidence = models.Evidence(
            property_id=prop.id,
            category="JURIDICO",
            fact=f"[{code}] {signal.get('evidence_text', '')}".strip(),
            interpretation=interpretation,
            hypothesis=f"Origem: {origem}" if origem else None,
            confidence=_confidence_label(signal.get("confidence")),
            source_excerpt=f"{JUDICIAL_SOURCE} — sinal {code} (severidade {signal.get('severity')})",
        )
        self.db.add(evidence)


def _digits(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _first_subject(subjects: list[dict[str, Any]]) -> str | None:
    for s in subjects:
        name = s.get("name")
        if name:
            return str(name)[:240]
    return None


def _split_parties(parties: list[dict[str, Any]]) -> dict[str, str | None]:
    ativos = [p.get("name") for p in parties if (p.get("role") or "").upper() in ("PLAINTIFF", "AUTOR", "ATIVO")]
    passivos = [p.get("name") for p in parties if (p.get("role") or "").upper() in ("DEFENDANT", "REU", "RÉU", "PASSIVO")]
    return {
        "ativo": ", ".join([a for a in ativos if a]) or None,
        "passivo": ", ".join([p for p in passivos if p]) or None,
    }
