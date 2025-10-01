"""Static pricing metadata for subscription tiers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class PlanPrice:
    stars: Optional[int]
    usd: float


@dataclass(frozen=True)
class PlanPricing:
    weekly: Optional[PlanPrice]
    monthly: Optional[PlanPrice]


_PRICING: Dict[str, PlanPricing] = {
    "free": PlanPricing(None, None),
    "lite": PlanPricing(
        weekly=PlanPrice(stars=29, usd=0.29),
        monthly=PlanPrice(stars=99, usd=1.99),
    ),
    "pro": PlanPricing(
        weekly=PlanPrice(stars=199, usd=2.99),
        monthly=PlanPrice(stars=499, usd=4.99),
    ),
}


def get_pricing(plan_key: str) -> PlanPricing:
    return _PRICING.get(plan_key.lower(), _PRICING["free"])
