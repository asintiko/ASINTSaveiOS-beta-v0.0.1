from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import CommandStat, PaymentTransaction, Spyusers


async def record_command_usage(session: AsyncSession, command: str) -> None:
    """Increment usage counter for a bot command."""
    command = command.lower().strip()
    if not command:
        return

    record = await session.scalar(select(CommandStat).where(CommandStat.command == command))
    now = datetime.utcnow()
    if record:
        record.count += 1
        record.updated_at = now
    else:
        record = CommandStat(command=command, count=1, created_at=now, updated_at=now)
        session.add(record)
    await session.flush()


async def record_payment_event(
    session: AsyncSession,
    *,
    user: Spyusers,
    plan: str,
    period: Optional[str],
    method: str,
    amount_stars: Optional[int] = None,
    amount_usd: Optional[float] = None,
    status: str = "success",
    is_manual: bool = False,
    initiator_id: Optional[int] = None,
    details: Optional[str] = None,
) -> None:
    transaction = PaymentTransaction(
        user_id=user.user_id,
        plan=plan.lower(),
        period=period.lower() if period else None,
        amount_stars=amount_stars,
        amount_usd=amount_usd,
        method=method.lower(),
        status=status.lower(),
        is_manual=is_manual,
        initiator_id=initiator_id,
        details=details,
    )
    session.add(transaction)
    await session.flush()


async def record_manual_subscription_grant(
    session: AsyncSession,
    user: Spyusers,
    *,
    admin_id: Optional[int],
    plan: str,
    period: str,
) -> None:
    await record_payment_event(
        session,
        user=user,
        plan=plan,
        period=period,
        method="manual",
        is_manual=True,
        initiator_id=admin_id,
    )
