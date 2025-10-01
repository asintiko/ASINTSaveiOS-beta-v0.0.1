import asyncio
import logging
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, FSInputFile, Message, User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.localization import DEFAULT_LANGUAGE, MESSAGES, get_text
from bot.markups.client import (
    agreement_keyboard,
    language_selection_keyboard,
    settings_keyboard,
    tut_kb,
)
from bot.subscription import (
    LimitSnapshot,
    SubscriptionProfileSnapshot,
    UsageSnapshot,
    get_profile_snapshot,
)
from bot.utils.check import is_bot_token
from bot.utils.creat import command_add_bot
from bot.utils.analytics import record_command_usage
from db import Spyusers
from logging_config import register_log_translations

logger = logging.getLogger(__name__)

register_log_translations(
    {
        "/start received with ref: %s from user %s": {
            "ru": "Получена команда /start с реферальным кодом %s от пользователя %s",
        },
        "Requested image not found: %s": {
            "ru": "Файл изображения не найден: %s",
        },
        "Invalid referral id provided: %s": {
            "ru": "Указан неверный реферальный идентификатор: %s",
        },
        "New user created: %s": {
            "ru": "Создан новый пользователь: %s",
        },
        "Failed to delete message %s: %s": {
            "ru": "Не удалось удалить сообщение %s: %s",
        },
        "Unexpected error deleting message %s: %s": {
            "ru": "Неожиданная ошибка при удалении сообщения %s: %s",
        },
        "Error in /start handler: %s": {
            "ru": "Ошибка в обработчике /start: %s",
        },
    }
)

_LANG_PROMPT_BILINGUAL = (
    f"{MESSAGES['language_prompt']['ru']}\n"
    f"{MESSAGES['language_prompt']['en']}"
)

_AGREEMENT_IMAGE_BY_LANG = {
    "ru": Path("images/соглашение.png"),
    "en": Path("images/USER.png"),
}

_WELCOME_IMAGE_BY_LANG = {
    "ru": Path("images/добро.png"),
    "en": Path("images/WELCOME.png"),
}

_BOT_INFO_CACHE: dict[str, TelegramUser] = {}


@lru_cache(maxsize=8)
def _load_image(path: Path) -> Optional[FSInputFile]:
    if not path.exists():
        logger.error("Requested image not found: %s", path)
        return None
    return FSInputFile(path.as_posix())


def start_router() -> Router:
    router = Router()

    async def _get_bot_info(bot: Bot) -> TelegramUser:
        cache_key = bot.token
        cached = _BOT_INFO_CACHE.get(cache_key)
        if cached is not None:
            return cached
        bot_info = await bot.get_me()
        _BOT_INFO_CACHE[cache_key] = bot_info
        return bot_info

    async def _get_or_create_user(
        session: AsyncSession,
        user_id: int,
        username: str | None,
        full_name: str | None,
        bot_username: str | None,
        ref_id: str | None,
    ) -> Spyusers:
        user = await session.scalar(select(Spyusers).where(Spyusers.user_id == user_id))
        now = datetime.utcnow()

        if user:
            user.username = username
            user.user_full_name = full_name
            if bot_username:
                user.bot_name = bot_username
            user.updated_at = now
            user.last_seen_at = now
            return user

        user = Spyusers(
            user_id=user_id,
            username=username,
            user_full_name=full_name,
            bot_name=bot_username,
            is_banned=False,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
        )

        if ref_id:
            try:
                user.ref_id = int(ref_id)
            except ValueError:
                logger.warning("Invalid referral id provided: %s", ref_id)

        session.add(user)
        await session.flush()
        logger.info("New user created: %s", user_id)
        return user

    async def _delete_message_safe(message: Message | None) -> None:
        if message is None:
            return
        try:
            await message.delete()
        except TelegramBadRequest as exc:
            logger.debug("Failed to delete message %s: %s", message.message_id, exc)
        except Exception as exc:  # pragma: no cover - unexpected issues
            logger.warning("Unexpected error deleting message %s: %s", message.message_id, exc)

    async def _send_language_prompt(bot: Bot, chat_id: int) -> None:
        await bot.send_message(
            chat_id=chat_id,
            text=_LANG_PROMPT_BILINGUAL,
            reply_markup=language_selection_keyboard(),
        )

    async def _send_agreement_prompt(bot: Bot, chat_id: int, language: str | None) -> None:
        lang = (language or DEFAULT_LANGUAGE).lower()
        image_path = _AGREEMENT_IMAGE_BY_LANG.get(lang)
        text = get_text("agreement_prompt", lang)
        if image_path:
            photo = _load_image(image_path)
            if photo:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text,
                    reply_markup=agreement_keyboard(lang),
                )
                return
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=agreement_keyboard(lang),
        )

    async def _send_business_mode_warning(bot: Bot, chat_id: int, language: str | None) -> None:
        await bot.send_message(
            chat_id=chat_id,
            text=get_text("business_mode_required", language),
        )

    async def _send_onboarding_completed(bot: Bot, chat_id: int, language: str | None) -> None:
        lang = (language or DEFAULT_LANGUAGE).lower()
        caption = get_text("start_welcome", lang)
        markup = tut_kb(lang)
        image_path = _WELCOME_IMAGE_BY_LANG.get(lang)
        if image_path:
            photo = _load_image(image_path)
            if photo:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=markup,
                )
                return
        await bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode="HTML",
            reply_markup=markup,
        )

    def _format_datetime_for_language(dt: datetime, language: str) -> str:
        if language == "ru":
            return dt.strftime("%d.%m.%Y %H:%M UTC")
        return dt.strftime("%Y-%m-%d %H:%M UTC")

    def _format_time_left(expires_at: datetime, now: datetime, language: str) -> str:
        delta = expires_at - now
        total_seconds = int(delta.total_seconds())
        if total_seconds <= 0:
            return get_text("profile_time_less_minute", language)

        minutes_total = total_seconds // 60
        days, remainder_minutes = divmod(minutes_total, 1440)
        hours, minutes = divmod(remainder_minutes, 60)

        parts: list[str] = []
        if days:
            parts.append(get_text("profile_time_part_day", language, value=str(days)))
        if hours and len(parts) < 2:
            parts.append(get_text("profile_time_part_hour", language, value=str(hours)))
        if minutes and len(parts) < 2:
            parts.append(get_text("profile_time_part_minute", language, value=str(minutes)))

        if not parts:
            return get_text("profile_time_less_minute", language)
        return " ".join(parts)

    def _format_limit_line(snapshot, language: str) -> str:
        if not isinstance(snapshot, LimitSnapshot):
            return ""

        scope_key = (
            "profile_limits_scope_week"
            if snapshot.scope == "week"
            else "profile_limits_scope_month"
        )
        scope_label = get_text(scope_key, language)
        line = get_text(
            "profile_limits_line",
            language,
            scope=scope_label,
            used=str(snapshot.used),
            limit=str(snapshot.limit),
            remaining=str(snapshot.remaining),
        )
        if snapshot.reset_at:
            reset_label = _format_datetime_for_language(snapshot.reset_at, language)
            line = f"{line} • {get_text('profile_limits_reset', language, date=reset_label)}"
        return line

    def _render_usage_section(header_key: str, usage, language: str) -> str:
        header = get_text(header_key, language)
        if not isinstance(usage, UsageSnapshot):
            return header

        lines: list[str] = [header]
        parts: list[str] = []
        if usage.weekly is not None:
            parts.append(_format_limit_line(usage.weekly, language))
        if usage.monthly is not None:
            parts.append(_format_limit_line(usage.monthly, language))

        filtered_parts = [part for part in parts if part]
        if filtered_parts:
            lines.extend(filtered_parts)
        else:
            lines.append(get_text("profile_limits_unlimited", language))
        return "\n".join(lines)

    def _render_profile_message(snapshot, language: str, now: datetime) -> str:
        if not isinstance(snapshot, SubscriptionProfileSnapshot):
            return get_text("profile_title", language)

        plan_label = get_text(f"subscription_plan_{snapshot.plan.key}", language)

        lines: list[str] = [
            get_text("profile_title", language),
            get_text("profile_plan", language, plan=plan_label),
        ]

        if snapshot.plan.key == "free":
            lines.append(get_text("profile_subscription_inactive", language))
        else:
            if snapshot.expires_at:
                time_left = _format_time_left(snapshot.expires_at, now, language)
                expires_str = _format_datetime_for_language(snapshot.expires_at, language)
                lines.append(
                    get_text(
                        "profile_subscription_active",
                        language,
                        date=expires_str,
                        time_left=time_left,
                    )
                )
            else:
                lines.append(get_text("profile_subscription_no_expiry", language))

        if snapshot.plan.key != "free" or snapshot.period is not None:
            if snapshot.period == "week":
                period_label = get_text("profile_period_week", language)
            elif snapshot.period == "month":
                period_label = get_text("profile_period_month", language)
            else:
                period_label = get_text("profile_period_unknown", language)
            lines.append(get_text("profile_period", language, period=period_label))

        lines.append("")
        lines.append(_render_usage_section("profile_media_header", snapshot.media, language))
        lines.append("")
        lines.append(
            _render_usage_section("profile_notifications_header", snapshot.notifications, language)
        )

        return "\n".join(lines)

    @router.message(CommandStart())
    async def start(
        message: Message,
        session: AsyncSession,
        bot: Bot,
        command: CommandObject | None = None,
    ) -> Any:
        try:
            await record_command_usage(session, "start")
            bot_info = await _get_bot_info(bot)
            ref_id = command.args if command and command.args else None
            user_id = message.from_user.id
            username = message.from_user.username if message.from_user else None
            full_name = message.from_user.full_name if message.from_user else ""

            logger.info("/start received with ref: %s from user %s", ref_id, user_id)

            user = await _get_or_create_user(
                session=session,
                user_id=user_id,
                username=username,
                full_name=full_name,
                bot_username=bot_info.username,
                ref_id=ref_id,
            )

            if user.is_banned:
                await message.answer(get_text("user_banned", user.language))
                return

            if user.language is None:
                await _send_language_prompt(bot, message.chat.id)
                return

            if not user.agreement_accepted:
                await _send_agreement_prompt(bot, message.chat.id, user.language)
                return

            if not bot_info.can_connect_to_business:
                await _send_business_mode_warning(bot, message.chat.id, user.language)
                return

            await _send_onboarding_completed(bot, message.chat.id, user.language)
        except Exception as ex:
            logger.exception("Error in /start handler: %s", ex)
        finally:
            await asyncio.sleep(0.05)

    @router.message(Command("settings"))
    async def settings(message: Message, session: AsyncSession) -> None:
        await record_command_usage(session, "settings")
        user = await session.scalar(select(Spyusers).where(Spyusers.user_id == message.from_user.id))
        if user:
            now = datetime.utcnow()
            user.updated_at = now
            user.last_seen_at = now
            language = user.language or DEFAULT_LANGUAGE
        else:
            language = DEFAULT_LANGUAGE
        title = get_text("settings_section_title", language)
        intro = get_text("settings_intro", language)
        await message.answer(
            text=f"<b>{title}</b>\n{intro}",
            parse_mode="HTML",
            reply_markup=settings_keyboard(language),
        )

    @router.callback_query(F.data == "profile:view")
    async def profile_view(
        callback: CallbackQuery,
        session: AsyncSession,
        language: str,
        bot: Bot,
    ) -> None:
        if not callback.from_user:
            await callback.answer()
            return

        user = await session.scalar(
            select(Spyusers).where(Spyusers.user_id == callback.from_user.id)
        )
        if not user:
            await callback.answer(get_text("start_required", language))
            return

        now = datetime.utcnow()
        user.updated_at = now
        user.last_seen_at = now

        snapshot = get_profile_snapshot(user, now)
        await session.flush()

        text = _render_profile_message(snapshot, language, now)
        await callback.answer()

        if callback.message is not None:
            await callback.message.answer(
                text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            return

        await bot.send_message(
            callback.from_user.id,
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )


    @router.callback_query(F.data.startswith("lang:"))
    async def language_callback(
        callback: CallbackQuery,
        session: AsyncSession,
        bot: Bot,
    ) -> None:
        if not callback.from_user:
            await callback.answer()
            return

        selected_language = callback.data.split(":", maxsplit=1)[1]
        if selected_language not in {"ru", "en"}:
            await callback.answer()
            return

        user = await session.scalar(select(Spyusers).where(Spyusers.user_id == callback.from_user.id))
        await callback.answer()
        await _delete_message_safe(callback.message)

        if not user:
            await _send_language_prompt(bot, callback.from_user.id)
            return

        now = datetime.utcnow()
        user.updated_at = now
        user.last_seen_at = now

        if user.language == selected_language:
            if not user.agreement_accepted:
                await _send_agreement_prompt(bot, callback.from_user.id, selected_language)
            return

        user.language = selected_language
        user.agreement_accepted = False
        user.agreement_accepted_at = None
        await session.flush()

        await _send_agreement_prompt(bot, callback.from_user.id, selected_language)

    @router.callback_query(F.data == "agreement:accept")
    async def agreement_accept(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
        if not callback.from_user:
            await callback.answer()
            return

        user = await session.scalar(select(Spyusers).where(Spyusers.user_id == callback.from_user.id))
        if not user:
            await callback.answer()
            await _send_language_prompt(bot, callback.from_user.id)
            return

        if user.agreement_accepted:
            await callback.answer(get_text("agreement_already_confirmed", user.language))
            return

        now = datetime.utcnow()
        user.agreement_accepted = True
        user.agreement_accepted_at = now
        user.updated_at = now
        user.last_seen_at = now
        await session.flush()

        await callback.answer()
        await _delete_message_safe(callback.message)
        await bot.send_message(
            chat_id=callback.from_user.id,
            text=get_text("agreement_confirmed", user.language),
        )

        bot_info = await _get_bot_info(bot)
        if not bot_info.can_connect_to_business:
            await _send_business_mode_warning(bot, callback.from_user.id, user.language)
            return

        await _send_onboarding_completed(bot, callback.from_user.id, user.language)

    @router.message(Command("add", magic=F.args.func(is_bot_token)))
    async def add(message: Message, bot: Bot, token: str, session: AsyncSession, language: str) -> Any:
        await record_command_usage(session, "add_bot")
        return await command_add_bot(
            message,
            bot,
            token,
            session=session,
            language=language,
        )

    return router
