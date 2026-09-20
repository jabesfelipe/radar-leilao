from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from .. import models


@dataclass(frozen=True)
class Pricing:
    provider: str
    model: str
    input_price_per_1m: Decimal
    output_price_per_1m: Decimal


def resolve_pricing(db: Session, provider: str, model: str) -> Pricing | None:
    pricing = db.scalar(select(models.LLMPricing).where(models.LLMPricing.provider == provider, models.LLMPricing.model == model, models.LLMPricing.active.is_(True)))
    if not pricing:
        return None
    return Pricing(pricing.provider, pricing.model, pricing.input_price_per_1m, pricing.output_price_per_1m)


def calculate_cost(input_tokens: int | None, output_tokens: int | None, pricing: Pricing | None) -> dict[str, Decimal | None]:
    if pricing is None or input_tokens is None or output_tokens is None:
        return {"input_cost": None, "output_cost": None, "total_cost": None}
    input_cost = Decimal(input_tokens) / Decimal(1_000_000) * pricing.input_price_per_1m
    output_cost = Decimal(output_tokens) / Decimal(1_000_000) * pricing.output_price_per_1m
    return {"input_cost": input_cost, "output_cost": output_cost, "total_cost": input_cost + output_cost}
