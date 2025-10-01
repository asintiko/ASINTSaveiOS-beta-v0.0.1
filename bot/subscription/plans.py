"""Subscription plan definitions and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from db import Spyusers


@dataclass(frozen=True)
class SubscriptionPlan:
    key: str
    allow_disappearing_media: bool
    store_messages: bool
    weekly_media_limit: Optional[int]
    monthly_media_limit: Optional[int]
    weekly_notification_limit: Optional[int]
    monthly_notification_limit: Optional[int]
    retention_days_weekly: Optional[int]
    retention_days_monthly: Optional[int]


_PLANS: Dict[str, SubscriptionPlan] = {
    "free": SubscriptionPlan(
        key="free",
        allow_disappearing_media=True,
        store_messages=False,
        weekly_media_limit=None,
        monthly_media_limit=3,
        weekly_notification_limit=None,
        monthly_notification_limit=50,
        retention_days_weekly=0,
        retention_days_monthly=0,
    ),
    "lite": SubscriptionPlan(
        key="lite",
        allow_disappearing_media=True,
        store_messages=True,
        weekly_media_limit=10,
        monthly_media_limit=25,
        weekly_notification_limit=250,
        monthly_notification_limit=500,
        retention_days_weekly=3,
        retention_days_monthly=3,
    ),
    "pro": SubscriptionPlan(
        key="pro",
        allow_disappearing_media=True,
        store_messages=True,
        weekly_media_limit=50,
        monthly_media_limit=150,
        weekly_notification_limit=None,
        monthly_notification_limit=None,
        retention_days_weekly=7,
        retention_days_monthly=30,
    ),
}

_DEFAULT_TIER = "free"
_WEEKLY_RESET_DELTA = timedelta(days=7)
_MONTHLY_RESET_DELTA = timedelta(days=30)


def get_plan(key: str) -> SubscriptionPlan:
    return _PLANS.get(key.lower(), _PLANS[_DEFAULT_TIER])


def resolve_user_plan(user: Spyusers, now: datetime) -> SubscriptionPlan:
    tier = (user.subscription_tier or _DEFAULT_TIER).lower()
    if tier != _DEFAULT_TIER and user.subscription_expires_at and user.subscription_expires_at <= now:
        user.subscription_tier = _DEFAULT_TIER
        user.subscription_expires_at = None
        user.subscription_period = None
        tier = _DEFAULT_TIER
    return get_plan(tier)


def _reset_media_counters_if_needed(user: Spyusers, now: datetime) -> None:
    if user.subscription_weekly_reset_at is None or now >= user.subscription_weekly_reset_at:
        user.subscription_weekly_media_count = 0
        user.subscription_weekly_reset_at = now + _WEEKLY_RESET_DELTA
    if user.subscription_monthly_reset_at is None or now >= user.subscription_monthly_reset_at:
        user.subscription_monthly_media_count = 0
        user.subscription_monthly_reset_at = now + _MONTHLY_RESET_DELTA


def _reset_notification_counters_if_needed(user: Spyusers, now: datetime) -> None:
    if (
        user.subscription_weekly_notification_reset_at is None
        or now >= user.subscription_weekly_notification_reset_at
    ):
        user.subscription_weekly_notification_count = 0
        user.subscription_weekly_notification_reset_at = now + _WEEKLY_RESET_DELTA
    if (
        user.subscription_monthly_notification_reset_at is None
        or now >= user.subscription_monthly_notification_reset_at
    ):
        user.subscription_monthly_notification_count = 0
        user.subscription_monthly_notification_reset_at = now + _MONTHLY_RESET_DELTA


def check_and_consume_disappearing_quota(
    user: Spyusers,
    plan: SubscriptionPlan,
    now: datetime,
) -> Tuple[bool, Optional[str], Optional[int], Optional[datetime]]:
    if not plan.allow_disappearing_media:
        return False, "not_allowed", None, None

    _reset_media_counters_if_needed(user, now)

    if plan.weekly_media_limit is not None and user.subscription_weekly_media_count >= plan.weekly_media_limit:
        return (
            False,
            "weekly_limit",
            plan.weekly_media_limit,
            user.subscription_weekly_reset_at,
        )
    if plan.monthly_media_limit is not None and user.subscription_monthly_media_count >= plan.monthly_media_limit:
        return (
            False,
            "monthly_limit",
            plan.monthly_media_limit,
            user.subscription_monthly_reset_at,
        )

    if plan.weekly_media_limit is not None:
        user.subscription_weekly_media_count += 1
    if plan.monthly_media_limit is not None:
        user.subscription_monthly_media_count += 1
    return True, None, None, None


def check_notification_quota(
    user: Spyusers,
    plan: SubscriptionPlan,
    now: datetime,
) -> Tuple[bool, Optional[str], Optional[int], Optional[datetime]]:
    if plan.weekly_notification_limit is None and plan.monthly_notification_limit is None:
        return True, None, None, None

    _reset_notification_counters_if_needed(user, now)

    if (
        plan.weekly_notification_limit is not None
        and user.subscription_weekly_notification_count >= plan.weekly_notification_limit
    ):
        return (
            False,
            "weekly_limit",
            plan.weekly_notification_limit,
            user.subscription_weekly_notification_reset_at,
        )
    if (
        plan.monthly_notification_limit is not None
        and user.subscription_monthly_notification_count >= plan.monthly_notification_limit
    ):
        return (
            False,
            "monthly_limit",
            plan.monthly_notification_limit,
            user.subscription_monthly_notification_reset_at,
        )

    if plan.weekly_notification_limit is not None:
        user.subscription_weekly_notification_count += 1
    if plan.monthly_notification_limit is not None:
        user.subscription_monthly_notification_count += 1
    return True, None, None, None


def compute_retention_deadline(
    plan: SubscriptionPlan,
    now: datetime,
    user: Spyusers,
) -> Optional[datetime]:
    if not plan.store_messages:
        return now

    period = (user.subscription_period or "month").lower()
    if period not in {"week", "month"}:
        period = "month"

    if period == "week":
        retention_days = plan.retention_days_weekly
    else:
        retention_days = plan.retention_days_monthly

    if retention_days is None:
        return user.subscription_expires_at
    if retention_days <= 0:
        return now
    return now + timedelta(days=retention_days)


def is_disappearing_message(message) -> bool:
    ttl_seconds = getattr(message, "ttl_seconds", None)
    return bool(ttl_seconds and ttl_seconds > 0)
