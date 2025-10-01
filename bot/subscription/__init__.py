"""Subscription utilities package."""

from .plans import (
    SubscriptionPlan,
    check_and_consume_disappearing_quota,
    check_notification_quota,
    compute_retention_deadline,
    get_plan,
    is_disappearing_message,
    resolve_user_plan,
)
from .pricing import PlanPrice, PlanPricing, get_pricing
from .service import (
    LimitSnapshot,
    SubscriptionPeriod,
    SubscriptionProfileSnapshot,
    UsageSnapshot,
    apply_subscription,
    get_active_plan,
    get_profile_snapshot,
)

__all__ = [
    "SubscriptionPlan",
    "SubscriptionPeriod",
    "PlanPrice",
    "PlanPricing",
    "LimitSnapshot",
    "UsageSnapshot",
    "SubscriptionProfileSnapshot",
    "apply_subscription",
    "check_and_consume_disappearing_quota",
    "check_notification_quota",
    "compute_retention_deadline",
    "get_active_plan",
    "get_profile_snapshot",
    "get_plan",
    "get_pricing",
    "is_disappearing_message",
    "resolve_user_plan",
]
