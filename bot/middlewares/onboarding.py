from __future__ import annotations

import logging
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

from aiogram import BaseMiddleware, Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.localization import DEFAULT_LANGUAGE, MESSAGES, get_text
from bot.markups.client import agreement_keyboard, language_selection_keyboard
from db import Spyusers
from logging_config import register_log_translations

logger = logging.getLogger(__name__)

register_log_translations(
    {
        "Prompt image not found: %s": {
            "ru": "Файл изображения подсказки не найден: %s",
        },
        "Cannot deliver %s to user %s: bot instance missing": {
            "ru": "Невозможно доставить %s пользователю %s: экземпляр бота отсутствует",
        },
        "Failed to send %s to user %s": {
            "ru": "Не удалось отправить %s пользователю %s",
        },
        "Flood control while sending %s to user %s. Retry after %ss": {
            "ru": "Флуд-контроль при отправке %s пользователю %s. Повтор через %s с",
        },
    }
)

_ALLOWED_COMMANDS = {"start", "settings"}
_ALLOWED_CALLBACKS = {"agreement:accept", "settings:change_language"}
_PROMPT_THROTTLE_SECONDS = 15.0
_PROMPT_AGREEMENT_IMAGES = {
    "ru": Path("images/соглашение.png"),
    "en": Path("images/USER.png"),
}
_prompt_cache: Dict[Tuple[int, str], float] = {}


@lru_cache(maxsize=4)
def _load_image(path: Path) -> Optional[FSInputFile]:
    if not path.exists():
        logger.error("Prompt image not found: %s", path)
        return None
    return FSInputFile(path.as_posix())


def _extract_command(message: Message) -> str | None:
    text = message.text or message.caption
    if not text or not text.startswith('/'):
        return None
    command = text.split()[0].split('@')[0]
    return command[1:].lower()


def _language_prompt() -> str:
    return f"{MESSAGES['language_prompt']['ru']}\n{MESSAGES['language_prompt']['en']}"


def _should_prompt(user_id: int, prompt_type: str) -> bool:
    now = time.monotonic()
    cache_key = (user_id, prompt_type)
    last_sent = _prompt_cache.get(cache_key)
    if last_sent and (now - last_sent) < _PROMPT_THROTTLE_SECONDS:
        return False
    _prompt_cache[cache_key] = now
    return True


async def _safe_send(coro, user_id: int, description: str) -> None:
    try:
        await coro
    except TelegramRetryAfter as exc:
        logger.warning(
            "Flood control while sending %s to user %s. Retry after %ss",
            description,
            user_id,
            exc.retry_after,
        )
    except Exception:
        logger.exception("Failed to send %s to user %s", description, user_id)


async def _prompt_via_message(
    message: Message,
    bot: Optional[Bot],
    user_id: int,
    text: str,
    description: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    language: str | None = None,
) -> None:
    chat = getattr(message, "chat", None)
    lang = (language or DEFAULT_LANGUAGE).lower()
    prompt_image_path = _PROMPT_AGREEMENT_IMAGES.get(lang)
    if (
        description == "agreement reminder"
        and prompt_image_path
        and (photo := _load_image(prompt_image_path))
    ):
        if chat and chat.type == "private":
            await _safe_send(
                message.answer_photo(
                    photo=photo,
                    caption=text,
                    reply_markup=reply_markup,
                ),
                user_id,
                description,
            )
            return
        if bot is not None:
            await _safe_send(
                bot.send_photo(
                    user_id,
                    photo=photo,
                    caption=text,
                    reply_markup=reply_markup,
                ),
                user_id,
                description,
            )
            return

    if chat and chat.type == "private":
        await _safe_send(message.answer(text, reply_markup=reply_markup), user_id, description)
        return

    if bot is not None:
        await _safe_send(bot.send_message(user_id, text, reply_markup=reply_markup), user_id, description)
    else:
        logger.warning("Cannot deliver %s to user %s: bot instance missing", description, user_id)


async def _prompt_via_callback(
    callback: CallbackQuery,
    bot: Optional[Bot],
    user_id: int,
    text: str,
    description: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    show_alert: bool = False,
    language: str | None = None,
) -> None:
    message = callback.message
    lang = (language or DEFAULT_LANGUAGE).lower()
    prompt_image_path = _PROMPT_AGREEMENT_IMAGES.get(lang)
    if (
        description == "agreement reminder"
        and prompt_image_path
        and (photo := _load_image(prompt_image_path))
    ):
        if message and message.chat.type == "private":
            if reply_markup:
                await _safe_send(
                    message.answer_photo(
                        photo=photo,
                        caption=text,
                        reply_markup=reply_markup,
                    ),
                    user_id,
                    description,
                )
            else:
                await _safe_send(
                    message.answer_photo(photo=photo, caption=text),
                    user_id,
                    description,
                )
            await callback.answer()
            return
        if bot is not None:
            await _safe_send(
                bot.send_photo(
                    user_id,
                    photo=photo,
                    caption=text,
                    reply_markup=reply_markup,
                ),
                user_id,
                description,
            )
        else:
            logger.warning("Cannot deliver %s to user %s: bot instance missing", description, user_id)
        await callback.answer()
        return

    if message and message.chat.type == "private":
        if reply_markup:
            await _safe_send(message.answer(text, reply_markup=reply_markup), user_id, description)
        else:
            await _safe_send(message.answer(text), user_id, description)
        await callback.answer()
        return

    if show_alert:
        await _safe_send(callback.answer(text, show_alert=True), user_id, description)
        return

    if bot is not None:
        await _safe_send(bot.send_message(user_id, text, reply_markup=reply_markup), user_id, description)
    else:
        logger.warning("Cannot deliver %s to user %s: bot instance missing", description, user_id)
    await callback.answer()


class OnboardingMiddleware(BaseMiddleware):
    """Ensure users finish onboarding before accessing bot features."""

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        session: AsyncSession | None = data.get("session")
        bot: Bot | None = data.get("bot")
        from_user = getattr(event, "from_user", None)

        if session is None or from_user is None:
            return await handler(event, data)

        user = await session.scalar(select(Spyusers).where(Spyusers.user_id == from_user.id))
        data["user_profile"] = user
        language = (user.language if user and user.language else DEFAULT_LANGUAGE)
        data["language"] = language

        if isinstance(event, Message):
            if getattr(event, "business_connection_id", None):
                return await handler(event, data)
            command = _extract_command(event)
            chat = getattr(event, "chat", None)
            is_private_chat = getattr(chat, "type", None) == "private"

            if user is None:
                if command == "start":
                    return await handler(event, data)
                if is_private_chat and _should_prompt(from_user.id, "language"):
                    await _prompt_via_message(
                        event,
                        bot,
                        from_user.id,
                        _language_prompt(),
                        "language prompt",
                        language_selection_keyboard(),
                        language,
                    )
                return None

            if user.is_banned:
                if is_private_chat and _should_prompt(from_user.id, "ban_notice"):
                    await _prompt_via_message(
                        event,
                        bot,
                        from_user.id,
                        get_text("user_banned", user.language),
                        "ban notice",
                        language=None,
                    )
                return None

            if user.language is None:
                if is_private_chat and _should_prompt(from_user.id, "language"):
                    await _prompt_via_message(
                        event,
                        bot,
                        from_user.id,
                        _language_prompt(),
                        "language prompt",
                        language_selection_keyboard(),
                        language,
                    )
                return None

            if not user.agreement_accepted:
                if command in _ALLOWED_COMMANDS:
                    return await handler(event, data)
                if is_private_chat and _should_prompt(from_user.id, "agreement"):
                    await _prompt_via_message(
                        event,
                        bot,
                        from_user.id,
                        get_text("agreement_reminder", user.language),
                        "agreement reminder",
                        agreement_keyboard(user.language),
                        user.language,
                    )
                return None

            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            data_value = event.data or ""
            if data_value.startswith("lang:"):
                return await handler(event, data)

            if user is None:
                await event.answer()
                if event.message and _should_prompt(from_user.id, "language"):
                    await _prompt_via_message(
                        event.message,
                        bot,
                        from_user.id,
                        _language_prompt(),
                        "language prompt",
                        language_selection_keyboard(),
                        language,
                    )
                return None

            if user.is_banned:
                if _should_prompt(from_user.id, "ban_notice"):
                    await _prompt_via_callback(
                        event,
                        bot,
                        from_user.id,
                        get_text("user_banned", user.language),
                        "ban notice",
                        show_alert=True,
                        language=user.language,
                    )
                else:
                    await event.answer()
                return None

            if user.language is None:
                await event.answer()
                if event.message and _should_prompt(from_user.id, "language"):
                    await _prompt_via_message(
                        event.message,
                        bot,
                        from_user.id,
                        _language_prompt(),
                        "language prompt",
                        language_selection_keyboard(),
                        language,
                    )
                return None

            if not user.agreement_accepted and data_value not in _ALLOWED_CALLBACKS:
                if _should_prompt(from_user.id, "agreement"):
                    await _prompt_via_callback(
                        event,
                        bot,
                        from_user.id,
                        get_text("agreement_reminder", user.language),
                        "agreement reminder",
                        agreement_keyboard(user.language),
                        language=user.language,
                    )
                else:
                    await event.answer()
                return None

            return await handler(event, data)

        return await handler(event, data)
