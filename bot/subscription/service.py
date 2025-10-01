"""Subscription lifecycle helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, Optional, cast

from db import Spyusers

from .plans import SubscriptionPlan, get_plan, resolve_user_plan

SubscriptionPeriod = Literal["week", "month"]

_PERIOD_TO_DELTA = {
    "week": timedelta(days=7),
    "month": timedelta(days=30),
}

_WEEKLY_RESET_DELTA = timedelta(days=7)
_MONTHLY_RESET_DELTA = timedelta(days=30)


@dataclass(frozen=True)
class LimitSnapshot:
    scope: SubscriptionPeriod
    limit: int
    used: int
    remaining: int
    reset_at: Optional[datetime]


@dataclass(frozen=True)
class UsageSnapshot:
    weekly: Optional[LimitSnapshot]
    monthly: Optional[LimitSnapshot]


@dataclass(frozen=True)
class SubscriptionProfileSnapshot:
    plan: SubscriptionPlan
    expires_at: Optional[datetime]
    period: Optional[SubscriptionPeriod]
    media: UsageSnapshot
    notifications: UsageSnapshot


def apply_subscription(
    user: Spyusers,
    plan_key: str,
    period: SubscriptionPeriod,
    now: datetime,
) -> SubscriptionPlan:
    plan = get_plan(plan_key)
    user.subscription_tier = plan.key
    duration = _PERIOD_TO_DELTA.get(period)
    if plan.key == "free":
        user.subscription_expires_at = None
        user.subscription_period = None
    elif duration is not None:
        user.subscription_expires_at = now + duration
        user.subscription_period = period
    else:
        user.subscription_expires_at = None
        user.subscription_period = None
    user.subscription_weekly_media_count = 0
    user.subscription_weekly_reset_at = now + timedelta(days=7)
    user.subscription_monthly_media_count = 0
    user.subscription_monthly_reset_at = now + timedelta(days=30)
    user.subscription_weekly_notification_count = 0
    user.subscription_weekly_notification_reset_at = now + timedelta(days=7)
    user.subscription_monthly_notification_count = 0
    user.subscription_monthly_notification_reset_at = now + timedelta(days=30)
    return plan


def get_active_plan(user: Spyusers, now: datetime) -> SubscriptionPlan:
    return resolve_user_plan(user, now)


def _snapshot_limit(
    *,
    limit: Optional[int],
    used: Optional[int],
    reset_at: Optional[datetime],
    scope: SubscriptionPeriod,
    now: datetime,
) -> Optional[LimitSnapshot]:
    if limit is None:
        return None

    used_value = used or 0
    if scope == "week":
        delta = _WEEKLY_RESET_DELTA
    else:
        delta = _MONTHLY_RESET_DELTA

    if reset_at is None or now >= reset_at:
        used_value = 0
        next_reset = now + delta
    else:
        next_reset = reset_at

    remaining = max(limit - used_value, 0)
    return LimitSnapshot(
        scope=scope,
        limit=limit,
        used=used_value,
        remaining=remaining,
        reset_at=next_reset,
    )


def _build_usage_snapshot(
    *,
    weekly_limit: Optional[int],
    weekly_used: Optional[int],
    weekly_reset: Optional[datetime],
    monthly_limit: Optional[int],
    monthly_used: Optional[int],
    monthly_reset: Optional[datetime],
    now: datetime,
) -> UsageSnapshot:
    weekly_snapshot = _snapshot_limit(
        limit=weekly_limit,
        used=weekly_used,
        reset_at=weekly_reset,
        scope="week",
        now=now,
    )
    monthly_snapshot = _snapshot_limit(
        limit=monthly_limit,
        used=monthly_used,
        reset_at=monthly_reset,
        scope="month",
        now=now,
    )
    return UsageSnapshot(weekly=weekly_snapshot, monthly=monthly_snapshot)


def get_profile_snapshot(user: Spyusers, now: datetime) -> SubscriptionProfileSnapshot:
    plan = resolve_user_plan(user, now)
    media_usage = _build_usage_snapshot(
        weekly_limit=plan.weekly_media_limit,
        weekly_used=user.subscription_weekly_media_count,
        weekly_reset=user.subscription_weekly_reset_at,
        monthly_limit=plan.monthly_media_limit,
        monthly_used=user.subscription_monthly_media_count,
        monthly_reset=user.subscription_monthly_reset_at,
        now=now,
    )
    notifications_usage = _build_usage_snapshot(
        weekly_limit=plan.weekly_notification_limit,
        weekly_used=user.subscription_weekly_notification_count,
        weekly_reset=user.subscription_weekly_notification_reset_at,
        monthly_limit=plan.monthly_notification_limit,
        monthly_used=user.subscription_monthly_notification_count,
        monthly_reset=user.subscription_monthly_notification_reset_at,
        now=now,
    )

    raw_period = user.subscription_period if user.subscription_period in {"week", "month"} else None
    period = cast(Optional[SubscriptionPeriod], raw_period)

    return SubscriptionProfileSnapshot(
        plan=plan,
        expires_at=user.subscription_expires_at,
        period=period,
        media=media_usage,
        notifications=notifications_usage,
    )
