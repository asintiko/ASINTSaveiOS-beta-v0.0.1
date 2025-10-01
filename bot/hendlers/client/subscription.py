"""Handlers for subscription management and payments."""

from __future__ import annotations

import asyncio
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.localization import BUTTONS, DEFAULT_LANGUAGE, get_text
from bot.payments.cryptobot import CryptoBotGateway
from bot.subscription import (
    SubscriptionPeriod,
    apply_subscription,
    get_pricing,
    resolve_user_plan,
)
from bot.subscription.pricing import PlanPrice, PlanPricing
from bot.utils.analytics import record_command_usage, record_payment_event
from config import ADMIN_IDS, CRYPTOBOT_ASSET, CRYPTOBOT_POLL_INTERVAL, CRYPTOBOT_POLL_TIMEOUT, CRYPTOBOT_TOKEN
from db import Spyusers

router = Router(name="subscription")

SESSION_FACTORY: async_sessionmaker | None = None

crypto_gateway = CryptoBotGateway(CRYPTOBOT_TOKEN)

_PLAN_ORDER: tuple[str, ...] = ("free", "lite", "pro")
_PERIODS: tuple[SubscriptionPeriod, ...] = ("week", "month")

_IMAGE_BY_LANG = {
    "menu": {
        "ru": Path("images/тарифы.png"),
        "en": Path("images/TARIFFS.png"),
    },
    "payment": {
        "ru": Path("images/оплата.png"),
        "en": Path("images/PAYMENT.png"),
    },
    "plan_free": {
        "ru": Path("images/подписка3.png"),
        "en": Path("images/подписка6.png"),
    },
    "plan_lite": {
        "ru": Path("images/подписка.png"),
        "en": Path("images/подписка4.png"),
    },
    "plan_pro": {
        "ru": Path("images/подписка2.png"),
        "en": Path("images/подписка5.png"),
    },
}

_PLAN_IMAGE_KEYS: dict[str, str] = {
    "free": "plan_free",
    "lite": "plan_lite",
    "pro": "plan_pro",
}


@dataclass(frozen=True)
class EffectivePrice:
    stars: Optional[int]
    usd: float
    discount_applied: bool


def _resolve_language(language: str | None) -> str:
    return (language or DEFAULT_LANGUAGE).lower()


def _get_image(image_key: str | None, language: str | None) -> Optional[FSInputFile]:
    if image_key is None:
        return None
    lang = _resolve_language(language)
    mapping = _IMAGE_BY_LANG.get(image_key, {})
    path = mapping.get(lang) or mapping.get(DEFAULT_LANGUAGE)
    if path and path.exists():
        return FSInputFile(path.as_posix())
    return None


async def _send_initial_step(
    message: Message,
    language: str,
    *,
    image_key: str | None,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    photo = _get_image(image_key, language)
    if photo:
        await message.answer_photo(photo=photo, caption=text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=reply_markup, disable_web_page_preview=True)


async def _send_callback_step(
    callback: CallbackQuery,
    bot: Bot,
    language: str,
    *,
    image_key: str | None,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = "HTML",
    disable_preview: bool = True,
) -> None:
    message = callback.message
    if message is not None:
        try:
            await message.delete()
        except TelegramBadRequest:
            pass
    chat_id = callback.from_user.id if callback.from_user else (message.chat.id if message else None)
    if chat_id is None:
        return
    photo = _get_image(image_key, language)
    if photo:
        await bot.send_photo(chat_id, photo=photo, caption=text, parse_mode=parse_mode, reply_markup=reply_markup)
    else:
        await bot.send_message(
            chat_id,
            text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            disable_web_page_preview=disable_preview,
        )


async def _edit_or_send(
    callback: CallbackQuery,
    bot: Bot,
    text: str,
    *,
    language: str,
    image_key: str | None = None,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = "HTML",
    disable_preview: bool = True,
) -> None:
    if image_key:
        await _send_callback_step(
            callback,
            bot,
            language,
            image_key=image_key,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_preview=disable_preview,
        )
        return

    message = callback.message
    if message is not None:
        try:
            await message.edit_text(
                text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_preview,
            )
            return
        except TelegramBadRequest:
            try:
                await message.delete()
            except TelegramBadRequest:
                pass

    chat_id = callback.from_user.id if callback.from_user else None
    if chat_id is None and callback.message is not None:
        chat_id = callback.message.chat.id
    if chat_id is None:
        return
    await bot.send_message(
        chat_id,
        text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
        disable_web_page_preview=disable_preview,
    )


def _calculate_effective_price(
    plan_key: str,
    period: SubscriptionPeriod,
    base_price: Optional[PlanPrice],
    user: Optional[Spyusers],
) -> Optional[EffectivePrice]:
    if base_price is None:
        return None

    stars = base_price.stars
    usd = base_price.usd
    discount_applied = False

    if (
        user
        and plan_key == "pro"
        and (user.subscription_tier or "").lower() == "lite"
        and user.subscription_expires_at
        and user.subscription_expires_at > datetime.utcnow()
    ):
        current_period = getattr(user, "subscription_period", None)
        if current_period == period:
            previous_pricing = get_pricing("lite")
            previous_price = previous_pricing.weekly if period == "week" else previous_pricing.monthly
            if previous_price:
                if stars is not None and previous_price.stars is not None:
                    discount_stars = int(round(previous_price.stars * 0.9))
                    new_stars = max(0, stars - discount_stars)
                    if new_stars != stars:
                        stars = new_stars
                        discount_applied = True
                if previous_price.usd is not None and base_price.usd is not None:
                    discount_usd = round(previous_price.usd * 0.9, 2)
                    new_usd = max(0.0, round(base_price.usd - discount_usd, 2))
                    if new_usd != usd:
                        usd = new_usd
                        discount_applied = True

    return EffectivePrice(stars=stars, usd=usd, discount_applied=discount_applied)


def _build_payment_pending_text(language: str, effective: Optional[EffectivePrice]) -> str:
    text = get_text("subscription_payment_pending", language)
    if effective and effective.discount_applied:
        text = f"{text}\n\n{get_text('subscription_upgrade_notice', language)}"
    return text


def _plan_name(plan_key: str, language: str) -> str:
    return get_text(f"subscription_plan_{plan_key}", language)


def _plan_image_key(plan_key: str) -> str | None:
    return _PLAN_IMAGE_KEYS.get(plan_key.lower())


def _period_name(period: SubscriptionPeriod, language: str) -> str:
    return get_text(f"subscription_period_{period}", language)


def _format_plan_summary(plan_key: str, language: str) -> str:
    summary_key = f"subscription_plan_{plan_key}_summary"
    summary = get_text(summary_key, language)
    return summary


def _plan_overview_keyboard(language: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for plan_key in _PLAN_ORDER:
        label = _format_plan_summary(plan_key, language)
        rows.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"subscription:plan:{plan_key}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _period_keyboard(plan_key: str, pricing: PlanPricing, language: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for period in _PERIODS:
        price: Optional[PlanPrice]
        if period == "week":
            price = pricing.weekly
        else:
            price = pricing.monthly
        if not price:
            continue
        period_name = _period_name(period, language)
        rows.append([
            InlineKeyboardButton(
                text=period_name,
                callback_data=f"subscription:period:{plan_key}:{period}",
            )
        ])
    rows.append([
        InlineKeyboardButton(
            text=BUTTONS["subscription_back"].get(language, BUTTONS["subscription_back"][DEFAULT_LANGUAGE]),
            callback_data="subscription:menu",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _payment_keyboard(
    plan_key: str,
    pricing: PlanPricing,
    period: SubscriptionPeriod,
    language: str,
    user: Optional[Spyusers],
    effective: Optional[EffectivePrice] = None,
) -> InlineKeyboardMarkup:
    base_price = pricing.weekly if period == "week" else pricing.monthly
    if effective is None:
        effective = _calculate_effective_price(plan_key, period, base_price, user)
    resolved_price: Optional[EffectivePrice]
    if effective is not None:
        resolved_price = effective
    elif base_price is not None:
        resolved_price = EffectivePrice(stars=base_price.stars, usd=base_price.usd, discount_applied=False)
    else:
        resolved_price = None
    buttons: list[list[InlineKeyboardButton]] = []
    if resolved_price and resolved_price.stars is not None and resolved_price.stars > 0:
        label_key = (
            "subscription_payment_stars_discount"
            if resolved_price.discount_applied
            else "subscription_payment_stars"
        )
        label = get_text(label_key, language, amount=str(resolved_price.stars))
        buttons.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"subscription:pay:stars:{plan_key}:{period}",
            )
        ])
    if resolved_price and crypto_gateway.is_configured:
        label_key = (
            "subscription_payment_crypto_discount"
            if resolved_price.discount_applied
            else "subscription_payment_crypto"
        )
        label = get_text(label_key, language, amount=f"{resolved_price.usd:.2f}", asset=CRYPTOBOT_ASSET)
        buttons.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"subscription:pay:crypto:{plan_key}:{period}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text=BUTTONS["subscription_back"].get(language, BUTTONS["subscription_back"][DEFAULT_LANGUAGE]),
            callback_data=f"subscription:plan:{plan_key}",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)



async def _send_plan_overview(message: Message, language: str) -> None:
    overview = get_text("subscription_plan_overview", language)
    await _send_initial_step(
        message,
        language,
        image_key="menu",
        text=overview,
        reply_markup=_plan_overview_keyboard(language),
    )


@router.message(Command("subscribe"))
async def command_subscribe(message: Message, language: str, session: AsyncSession) -> None:
    await record_command_usage(session, "subscribe")
    if message.from_user:
        user = await session.scalar(select(Spyusers).where(Spyusers.user_id == message.from_user.id))
        if user:
            now = datetime.utcnow()
            user.updated_at = now
            user.last_seen_at = now
    await _send_plan_overview(message, language)


@router.message(Command("plans"))
async def command_plans(message: Message, language: str, session: AsyncSession) -> None:
    await record_command_usage(session, "plans")
    if message.from_user:
        user = await session.scalar(select(Spyusers).where(Spyusers.user_id == message.from_user.id))
        if user:
            now = datetime.utcnow()
            user.updated_at = now
            user.last_seen_at = now
    overview = get_text("subscription_marketing", language)
    await message.answer(overview, parse_mode="HTML", disable_web_page_preview=True)


@router.callback_query(F.data == "subscription:menu")
async def callback_menu(callback: CallbackQuery, language: str, bot: Bot) -> None:
    await callback.answer()
    await _edit_or_send(
        callback,
        bot,
        get_text("subscription_plan_overview", language),
        language=language,
        reply_markup=_plan_overview_keyboard(language),
        image_key="menu",
    )


@router.callback_query(F.data.startswith("subscription:plan:"))
async def callback_plan(callback: CallbackQuery, language: str, bot: Bot, session: AsyncSession) -> None:
    await callback.answer()
    plan_key = callback.data.split(":", 2)[2]
    pricing = get_pricing(plan_key)
    plan_label = _plan_name(plan_key, language)
    plan_details = get_text(f"subscription_plan_{plan_key}_details", language)
    prompt: str | None = None
    if plan_key != "free":
        prompt = get_text("subscription_select_period", language, plan=plan_label)
    plan_image_key = _plan_image_key(plan_key)

    user = None
    if callback.from_user:
        user = await session.scalar(select(Spyusers).where(Spyusers.user_id == callback.from_user.id))
    now = datetime.utcnow()
    eligible_for_upgrade = False
    if user:
        resolve_user_plan(user, now)
        await session.flush()
        current_tier = (user.subscription_tier or "").lower()
        has_active_subscription = (
            current_tier != "free"
            and (user.subscription_expires_at is None or user.subscription_expires_at > now)
        )
        if (
            plan_key == "pro"
            and current_tier == "lite"
            and user.subscription_expires_at is not None
            and user.subscription_expires_at > now
        ):
            eligible_for_upgrade = True
        if has_active_subscription and not eligible_for_upgrade:
            if user.subscription_expires_at:
                date_str = user.subscription_expires_at.strftime("%Y-%m-%d %H:%M UTC")
                message = get_text("subscription_already_active", language, date=date_str)
            else:
                message = get_text("subscription_already_active_no_expiry", language)
            await _edit_or_send(
                callback,
                bot,
                message,
                language=language,
                parse_mode="HTML",
                image_key=plan_image_key,
            )
            return

    sections: list[str] = [plan_details.strip()]
    if eligible_for_upgrade:
        sections.append(get_text("subscription_upgrade_notice", language).strip())
    if prompt:
        sections.append(prompt)
    full_text = "\n\n".join(sections)
    await _edit_or_send(
        callback,
        bot,
        full_text,
        language=language,
        reply_markup=_period_keyboard(plan_key, pricing, language),
        parse_mode="HTML",
        image_key=plan_image_key,
    )


@router.callback_query(F.data.startswith("subscription:period:"))
async def callback_period(
    callback: CallbackQuery,
    language: str,
    bot: Bot,
    session: AsyncSession,
) -> None:
    await callback.answer()
    if callback.from_user is None:
        return
    _, _, plan_key, period = callback.data.split(":", 3)
    pricing = get_pricing(plan_key)
    plan_label = _plan_name(plan_key, language)
    period_enum: SubscriptionPeriod = "week" if period == "week" else "month"  # type: ignore[assignment]
    period_label = _period_name(period_enum, language)
    plan_image_key = _plan_image_key(plan_key)

    user = await session.scalar(select(Spyusers).where(Spyusers.user_id == callback.from_user.id))
    now = datetime.utcnow()
    eligible_for_upgrade = False
    if user:
        resolve_user_plan(user, now)
        await session.flush()
        current_tier = (user.subscription_tier or "").lower()
        has_active_subscription = (
            current_tier != "free"
            and (user.subscription_expires_at is None or user.subscription_expires_at > now)
        )
        if (
            plan_key == "pro"
            and current_tier == "lite"
            and user.subscription_expires_at is not None
            and user.subscription_expires_at > now
        ):
            eligible_for_upgrade = True
            current_period = getattr(user, "subscription_period", None)
            if current_period is not None and current_period != period_enum:
                await _edit_or_send(
                    callback,
                    bot,
                    get_text("subscription_upgrade_period_mismatch", language),
                    language=language,
                    parse_mode="HTML",
                    image_key=plan_image_key,
                )
                return
        if has_active_subscription and not eligible_for_upgrade:
            if user.subscription_expires_at:
                date_str = user.subscription_expires_at.strftime("%Y-%m-%d %H:%M UTC")
                await _edit_or_send(
                    callback,
                    bot,
                    get_text("subscription_already_active", language, date=date_str),
                    language=language,
                    parse_mode="HTML",
                    image_key=plan_image_key,
                )
            else:
                await _edit_or_send(
                    callback,
                    bot,
                    get_text("subscription_already_active_no_expiry", language),
                    language=language,
                    parse_mode="HTML",
                    image_key=plan_image_key,
                )
            return

    base_price = pricing.weekly if period_enum == "week" else pricing.monthly
    effective = _calculate_effective_price(plan_key, period_enum, base_price, user)
    prompt = get_text("subscription_select_payment", language, plan=plan_label, period=period_label)
    if effective and effective.discount_applied:
        prompt = f"{prompt}\n\n{get_text('subscription_upgrade_notice', language)}"
    await _edit_or_send(
        callback,
        bot,
        prompt,
        language=language,
        reply_markup=_payment_keyboard(
            plan_key,
            pricing,
            period_enum,
            language,
            user,
            effective=effective,
        ),
        parse_mode="HTML",
        image_key="payment",
    )


async def _notify_admins(bot: Bot, text: str) -> None:
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, disable_web_page_preview=True)
        except Exception:
            continue


async def _activate_subscription(
    session: AsyncSession,
    user: Spyusers,
    plan_key: str,
    period: SubscriptionPeriod,
    language: str,
    bot: Bot,
    method: str,
    *,
    amount_stars: int | None = None,
    amount_usd: float | None = None,
    initiator_id: int | None = None,
) -> str:
    now = datetime.utcnow()
    apply_subscription(user, plan_key, period, now)
    user.updated_at = now
    user.last_seen_at = now
    plan_label = _plan_name(plan_key, language)
    if user.subscription_expires_at:
        date_str = user.subscription_expires_at.strftime("%Y-%m-%d %H:%M UTC")
        message = get_text("subscription_payment_success", language, plan=plan_label, date=date_str)
    else:
        message = get_text("subscription_payment_success_no_expiry", language, plan=plan_label)
    await session.flush()
    await record_payment_event(
        session=session,
        user=user,
        plan=plan_key,
        period=str(period),
        method=method,
        amount_stars=amount_stars,
        amount_usd=amount_usd,
        initiator_id=initiator_id,
    )
    admin_text = get_text(
        "subscription_admin_notification",
        language,
        user_id=str(user.user_id),
        plan=plan_label,
        period=_period_name(period, language),
        method=method,
    )
    await _notify_admins(bot, admin_text)
    return message


@router.callback_query(F.data.startswith("subscription:pay:stars:"))
async def callback_pay_stars(
    callback: CallbackQuery,
    bot: Bot,
    language: str,
    session: AsyncSession,
) -> None:
    await callback.answer()
    if callback.from_user is None:
        return

    _, _, _, plan_key, period = callback.data.split(":", 4)
    period_enum: SubscriptionPeriod = "week" if period == "week" else "month"  # type: ignore[assignment]
    pricing = get_pricing(plan_key)
    base_price = pricing.weekly if period_enum == "week" else pricing.monthly
    if not base_price or base_price.stars is None:
        if callback.message:
            await callback.message.answer(get_text("subscription_payment_failed", language))
        return
    plan_image_key = _plan_image_key(plan_key)

    user = await session.scalar(select(Spyusers).where(Spyusers.user_id == callback.from_user.id))
    now = datetime.utcnow()
    eligible_for_upgrade = False
    if user:
        resolve_user_plan(user, now)
        await session.flush()
        current_tier = (user.subscription_tier or "").lower()
        has_active_subscription = (
            current_tier != "free"
            and (user.subscription_expires_at is None or user.subscription_expires_at > now)
        )
        if (
            plan_key == "pro"
            and current_tier == "lite"
            and user.subscription_expires_at is not None
            and user.subscription_expires_at > now
        ):
            eligible_for_upgrade = True
            current_period = getattr(user, "subscription_period", None)
            if current_period is not None and current_period != period_enum:
                await _edit_or_send(
                    callback,
                    bot,
                    get_text("subscription_upgrade_period_mismatch", language),
                    language=language,
                    parse_mode="HTML",
                    image_key=plan_image_key,
                )
                return
        if has_active_subscription and not eligible_for_upgrade:
            if user.subscription_expires_at:
                date_str = user.subscription_expires_at.strftime("%Y-%m-%d %H:%M UTC")
                await _edit_or_send(
                    callback,
                    bot,
                    get_text("subscription_already_active", language, date=date_str),
                    language=language,
                    parse_mode="HTML",
                    image_key=plan_image_key,
                )
            else:
                await _edit_or_send(
                    callback,
                    bot,
                    get_text("subscription_already_active_no_expiry", language),
                    language=language,
                    parse_mode="HTML",
                    image_key=plan_image_key,
                )
            return

    effective = _calculate_effective_price(plan_key, period_enum, base_price, user)
    star_amount = base_price.stars
    if effective and effective.stars is not None:
        star_amount = effective.stars
    if star_amount is None or star_amount <= 0:
        if callback.message:
            await callback.message.answer(get_text("subscription_payment_failed", language))
        return

    plan_label = _plan_name(plan_key, language)
    period_label = _period_name(period_enum, language)
    title = f"{plan_label} — {period_label}"
    description = get_text("subscription_marketing_plain", language)
    payload = f"stars:{plan_key}:{period}"
    prices = [LabeledPrice(label=title, amount=star_amount)]

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=title,
        description=description,
        payload=payload,
        provider_token="XTR",
        currency="XTR",
        prices=prices,
        need_name=False,
        need_email=False,
        need_phone_number=False,
        is_flexible=False,
    )

    await _edit_or_send(
        callback,
        bot,
        _build_payment_pending_text(language, effective),
        language=language,
        parse_mode="HTML",
        image_key="payment",
    )



async def _poll_crypto_invoice(
    invoice_id: str,
    payment_method: str,
    user_id: int,
    plan_key: str,
    period: SubscriptionPeriod,
    language: str,
    bot: Bot,
    sessionmaker: async_sessionmaker,
    amount_usd: float,
) -> None:
    assert crypto_gateway.is_configured
    paid = await crypto_gateway.poll_until_paid(
        invoice_id=invoice_id,
        interval=CRYPTOBOT_POLL_INTERVAL,
        timeout=CRYPTOBOT_POLL_TIMEOUT,
    )
    async with sessionmaker() as session:
        async with session.begin():
            user = await session.scalar(select(Spyusers).where(Spyusers.user_id == user_id))
            if not user:
                return
            if paid:
                message = await _activate_subscription(
                    session=session,
                    user=user,
                    plan_key=plan_key,
                    period=period,
                    language=user.language or language or DEFAULT_LANGUAGE,
                    bot=bot,
                    method=payment_method,
                    amount_usd=amount_usd,
                )
                await bot.send_message(user_id, message, parse_mode="HTML", disable_web_page_preview=True)
            else:
                await bot.send_message(
                    user_id,
                    get_text("subscription_payment_failed", user.language or language or DEFAULT_LANGUAGE),
                    disable_web_page_preview=True,
                )
                admin_text = get_text(
                    "subscription_admin_notification",
                    user.language or language or DEFAULT_LANGUAGE,
                    user_id=str(user_id),
                    plan=_plan_name(plan_key, user.language or language or DEFAULT_LANGUAGE),
                    period=_period_name(period, user.language or language or DEFAULT_LANGUAGE),
                    method=payment_method + " (failed)",
                )
                await _notify_admins(bot, admin_text)


@router.callback_query(F.data.startswith("subscription:pay:crypto:"))
async def callback_pay_crypto(
    callback: CallbackQuery,
    bot: Bot,
    language: str,
    session: AsyncSession,
    sessionmaker: Optional[async_sessionmaker] = None,
) -> None:
    await callback.answer()
    if callback.from_user is None or not crypto_gateway.is_configured:
        if callback.message:
            await callback.message.answer(get_text("subscription_payment_failed", language))
        return

    if sessionmaker is None:
        sessionmaker = SESSION_FACTORY
    if sessionmaker is None:
        if callback.message:
            await callback.message.answer(get_text("subscription_payment_failed", language))
        return

    _, _, _, plan_key, period = callback.data.split(":", 4)
    period_enum: SubscriptionPeriod = "week" if period == "week" else "month"  # type: ignore[assignment]
    pricing = get_pricing(plan_key)
    base_price = pricing.weekly if period_enum == "week" else pricing.monthly
    if not base_price:
        if callback.message:
            await callback.message.answer(get_text("subscription_payment_failed", language))
        return
    plan_image_key = _plan_image_key(plan_key)

    user = await session.scalar(select(Spyusers).where(Spyusers.user_id == callback.from_user.id))
    now = datetime.utcnow()
    if user:
        resolve_user_plan(user, now)
        await session.flush()
        current_tier = (user.subscription_tier or "").lower()
        has_active_subscription = (
            current_tier != "free"
            and (user.subscription_expires_at is None or user.subscription_expires_at > now)
        )
        eligible_for_upgrade = False
        if (
            plan_key == "pro"
            and current_tier == "lite"
            and user.subscription_expires_at is not None
            and user.subscription_expires_at > now
        ):
            eligible_for_upgrade = True
            current_period = getattr(user, "subscription_period", None)
            if current_period is not None and current_period != period_enum:
                await _edit_or_send(
                    callback,
                    bot,
                    get_text("subscription_upgrade_period_mismatch", language),
                    language=language,
                    parse_mode="HTML",
                    image_key=plan_image_key,
                )
                return
        if has_active_subscription and not eligible_for_upgrade:
            if user.subscription_expires_at:
                date_str = user.subscription_expires_at.strftime("%Y-%m-%d %H:%M UTC")
                await _edit_or_send(
                    callback,
                    bot,
                    get_text("subscription_already_active", language, date=date_str),
                    language=language,
                    parse_mode="HTML",
                    image_key=plan_image_key,
                )
            else:
                await _edit_or_send(
                    callback,
                    bot,
                    get_text("subscription_already_active_no_expiry", language),
                    language=language,
                    parse_mode="HTML",
                    image_key=plan_image_key,
                )
            return

    effective = _calculate_effective_price(plan_key, period_enum, base_price, user)
    amount = base_price.usd
    if effective:
        amount = effective.usd
    invoice = await crypto_gateway.create_invoice(
        user_id=callback.from_user.id,
        plan_key=plan_key,
        asset=CRYPTOBOT_ASSET,
        amount=amount,
        description=_plan_name(plan_key, language),
        payload=f"crypto:{plan_key}:{period}:{callback.from_user.id}",
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="➡️ Оплатить", url=invoice.pay_url)]]
    )
    await _edit_or_send(
        callback,
        bot,
        _build_payment_pending_text(language, effective),
        language=language,
        reply_markup=keyboard,
        parse_mode="HTML",
        image_key="payment",
    )

    asyncio.create_task(
        _poll_crypto_invoice(
            invoice_id=invoice.invoice_id,
            payment_method="CryptoBot",
            user_id=callback.from_user.id,
            plan_key=plan_key,
            period=period_enum,
            language=language,
            bot=bot,
            sessionmaker=sessionmaker,
            amount_usd=amount,
        )
    )



@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    payload = query.invoice_payload or ""
    if payload.startswith("stars:"):
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Unsupported payment method")


@router.message(F.successful_payment)
async def handle_successful_payment(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    language: str,
) -> None:
    payment = message.successful_payment
    if not payment or not payment.invoice_payload:
        return
    payload = payment.invoice_payload
    if not payload.startswith("stars:"):
        return
    _, plan_key, period = payload.split(":", 2)
    user = await session.scalar(select(Spyusers).where(Spyusers.user_id == message.from_user.id))
    if not user:
        return
    result_message = await _activate_subscription(
        session=session,
        user=user,
        plan_key=plan_key,
        period=period,  # type: ignore[arg-type]
        language=language,
        bot=bot,
        method="Telegram Stars",
        amount_stars=payment.total_amount,
    )
    await message.answer(result_message, parse_mode="HTML", disable_web_page_preview=True)


def subscription_router(sessionmaker: async_sessionmaker | None = None) -> Router:
    global SESSION_FACTORY
    if sessionmaker is not None:
        SESSION_FACTORY = sessionmaker
    return router
