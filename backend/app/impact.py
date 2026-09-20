from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


SUPPORTED_DOMAINS = ("documental", "juridico", "financeiro", "mercado", "checklist")
SUPPORTED_AGENTS = SUPPORTED_DOMAINS

# Impactos explícitos dos eventos já existentes no domínio. A ordem é estável
# para manter respostas determinísticas e facilitar auditoria.
EVENT_IMPACTS: dict[str, tuple[str, ...]] = {
    "IMOVEL_CADASTRADO": ("documental", "financeiro", "juridico", "mercado", "checklist"),
    "DOCUMENTO_ADICIONADO": ("documental", "juridico", "checklist"),
    "DOCUMENTO_VERSAO_ADICIONADA": ("documental", "juridico", "checklist"),
    "EVIDENCIA_REGISTRADA": ("checklist", "juridico", "documental"),
    "EVIDENCIA_VINCULADA": ("checklist", "juridico", "documental", "financeiro"),
    "EVIDENCIA_DOCUMENTAL_NORMALIZADA": ("documental", "juridico", "checklist"),
    "MATRICULA_CADASTRADA": ("juridico", "checklist"),
    "MATRICULA_EXTRAIDA": ("juridico", "checklist"),
    "EDITAL_CADASTRADO": ("documental", "juridico", "financeiro", "checklist"),
    "EDITAL_EXTRAIDO": ("documental", "juridico", "financeiro", "checklist"),
    "PROCESSO_ADICIONADO": ("juridico", "checklist", "financeiro"),
    "DIVIDA_ADICIONADA": ("financeiro", "checklist"),
    "CUSTO_ADICIONADO": ("financeiro", "checklist"),
    "COMPARAVEL_ADICIONADO": ("mercado", "financeiro"),
    "OCUPACAO_ATUALIZADA": ("financeiro", "checklist"),
    "LEILAO_ATUALIZADO": ("financeiro", "checklist"),
    "CHECKLIST_ATUALIZADO": ("checklist", "financeiro", "juridico"),
}


@dataclass(frozen=True)
class ImpactAnalysisResult:
    property_id: int
    event_type: str
    entity_type: str | None
    entity_id: int | None
    affected_domains: list[str]
    affected_checklist_keys: list[str]
    recommended_agents: list[str]
    reason: str
    requires_reanalysis: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ImpactAnalyzer:
    """Analisa impacto de eventos sem efeitos colaterais ou execução de agentes."""

    def analyze(
        self,
        property_id: int,
        event_type: str,
        entity_type: str | None = None,
        entity_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> ImpactAnalysisResult:
        normalized_event = str(event_type or "").strip().upper()
        domains = list(EVENT_IMPACTS.get(normalized_event, ()))
        # O sistema não possui um domínio/agente operacional de desocupação;
        # ocupação continua representada pelos domínios financeiros/checklist.
        domains = [domain for domain in domains if domain in SUPPORTED_DOMAINS]
        if not domains:
            return ImpactAnalysisResult(
                property_id=property_id,
                event_type=normalized_event,
                entity_type=entity_type,
                entity_id=entity_id,
                affected_domains=[],
                affected_checklist_keys=[],
                recommended_agents=[],
                reason="Evento sem regra de impacto configurada",
                requires_reanalysis=False,
            )
        return ImpactAnalysisResult(
            property_id=property_id,
            event_type=normalized_event,
            entity_type=entity_type,
            entity_id=entity_id,
            affected_domains=domains,
            affected_checklist_keys=[],
            recommended_agents=[agent for agent in SUPPORTED_AGENTS if agent in domains],
            reason="Impacto determinado pela regra do evento existente; checklist keys específicas não foram inferidas.",
            requires_reanalysis=True,
        )
