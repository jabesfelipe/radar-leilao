"""Contrato e providers de consulta municipal de débito (Etapa E).

O NÚCLEO não conhece portais: fala apenas com o contrato ``MunicipalDebtProvider``.
Cada provider é isolado, determinístico e testável. Esta etapa entrega o contrato, o
provider MANUAL/ASSISTIDO (sempre válido) e o registry de seleção por município/fonte.

NENHUMA consulta externa, scraping, automação ou contorno de CAPTCHA/autenticação é
executada. Providers automáticos reais só entram por município com viabilidade
confirmada + autorização (Etapa F futura). Até lá, a seleção recai no provider manual.

Separação de responsabilidades (SPEC-ADAPTADORES): consulta → normalização →
persistência → consolidação são camadas distintas. Aqui vive apenas a CONSULTA (que
produz um ``DebtQueryResult`` normalizável); a persistência/consolidação ficam no
serviço (``debt_query_service``).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DebtQueryContext:
    """Entrada padronizada de uma consulta. ``identifier`` é o identificador exigido
    pela fonte (ex.: Inscrição Imobiliária). ``payload`` carrega dados informados no
    fluxo assistido (valores digitados a partir do portal oficial pelo operador)."""
    property_id: int
    debt_type_code: str
    municipality_id: int | None = None
    source_id: int | None = None
    identifier: str | None = None
    opportunity_id: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class DebtQueryResult:
    """Saída normalizada de uma consulta. ``status`` segue ``DEBT_QUERY_STATUSES``.
    ``items`` são lançamentos prontos para normalização em ``PropertyDebt`` (a
    persistência é responsabilidade do serviço). ``message`` registra limitação/erro
    estruturado. ``evidence`` guarda metadados da origem para rastreabilidade."""
    status: str
    provider: str
    provider_version: str
    mode: str
    items: list[dict[str, Any]] = field(default_factory=list)
    message: str | None = None
    evidence: dict[str, Any] | None = None
    duration_ms: int | None = None
    attempts: int = 1


class MunicipalDebtProvider(Protocol):
    name: str
    version: str
    def consultar(self, db: Session, ctx: DebtQueryContext) -> DebtQueryResult: ...


class ManualAssistedProvider:
    """Provider MANUAL/ASSISTIDO — o fallback sempre válido. Não acessa portal: o
    operador consulta a fonte oficial e informa os valores; o provider apenas
    estrutura/valida o resultado informado, preservando a origem e a confiabilidade
    (nunca marca ESTIMADO como OFICIAL). Determinístico; sem rede."""
    name = "manual_assistida"
    version = "1.0"

    def consultar(self, db: Session, ctx: DebtQueryContext) -> DebtQueryResult:
        started = time.monotonic()
        payload = ctx.payload or {}
        informed = payload.get("itens") or payload.get("items")
        # Sem dado informado: a consulta assistida fica aguardando ação manual (não
        # é erro nem "sem ocorrência" — ausência de resultado ≠ ausência de débito).
        if not informed:
            if payload.get("sem_ocorrencia") is True:
                status = "SEM_OCORRENCIA"
                message = "Consulta assistida: operador registrou ausência de ocorrência na fonte."
                items: list[dict[str, Any]] = []
            else:
                status = "REQUER_INTERVENCAO_MANUAL"
                message = "Aguardando o operador informar o resultado consultado na fonte oficial."
                items = []
        else:
            status = "CONCLUIDA"
            message = payload.get("mensagem")
            items = [self._normalize_item(ctx, it) for it in informed]
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info("debt_query provider=%s municipality=%s type=%s status=%s", self.name, ctx.municipality_id, ctx.debt_type_code, status)
        return DebtQueryResult(
            status=status, provider=self.name, provider_version=self.version, mode="ASSISTIDA",
            items=items, message=message, duration_ms=duration_ms, attempts=1,
            evidence={"origem": "consulta_assistida", "identificador": ctx.identifier, "fonte_id": ctx.source_id},
        )

    @staticmethod
    def _normalize_item(ctx: DebtQueryContext, raw: dict[str, Any]) -> dict[str, Any]:
        # Mantém os campos conhecidos de PropertyDebt; o serviço revalida via
        # debts_service.normalize_debt_payload (ESTIMADO nunca vira OFICIAL).
        item = {
            "debt_type_code": raw.get("debt_type_code") or ctx.debt_type_code,
            "municipality_id": ctx.municipality_id,
            "original_amount": raw.get("original_amount"),
            "updated_amount": raw.get("updated_amount"),
            "reference_date": raw.get("reference_date"),
            "competence": raw.get("competence"),
            "status": (raw.get("status") or "INFORMADO"),
            "reliability": (raw.get("reliability") or "INFORMADO"),
            "origin": raw.get("origin") or "Consulta assistida (fonte oficial informada pelo operador)",
            "external_id": raw.get("external_id"),
            "observations": raw.get("observations"),
        }
        return item


# Registry de providers. A seleção é por DADO (cobertura/fonte), nunca por condicional
# fixa de cidade. Hoje só há o provider manual/assistido; providers automáticos reais
# serão registrados aqui por município conforme viabilidade confirmada + autorização.
_PROVIDERS: dict[str, MunicipalDebtProvider] = {
    ManualAssistedProvider.name: ManualAssistedProvider(),
}


def register_provider(provider: MunicipalDebtProvider) -> None:
    """Registra um provider (ponto de extensão para providers automáticos futuros)."""
    _PROVIDERS[provider.name] = provider


def available_providers() -> list[str]:
    return sorted(_PROVIDERS)


def select_provider(db: Session, *, municipality_id: int | None, debt_type_code: str) -> MunicipalDebtProvider:
    """Seleciona o provider para (município × tipo) a partir da MATRIZ de cobertura.

    Se a cobertura indicar integração disponível E houver um provider automático
    registrado com esse nome, usa-o; caso contrário, recai no manual/assistido
    (fallback sempre válido). A ausência de integração NUNCA derruba a apuração."""
    if municipality_id is not None:
        cov = db.scalar(
            select(models.MunicipalityCoverage).where(
                models.MunicipalityCoverage.municipality_id == municipality_id,
                models.MunicipalityCoverage.debt_type_code == debt_type_code,
                models.MunicipalityCoverage.active.is_(True),
            )
        )
        if cov is not None and cov.level == "INTEGRACAO_DISPONIVEL":
            # Convenção: provider automático nomeado por município (quando existir).
            auto_name = f"auto_{municipality_id}_{debt_type_code.lower()}"
            if auto_name in _PROVIDERS:
                return _PROVIDERS[auto_name]
    return _PROVIDERS[ManualAssistedProvider.name]
