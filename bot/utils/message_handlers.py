import os
import asyncio
import logging
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import Message, FSInputFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.localization import DEFAULT_LANGUAGE, MEDIA_TYPE_LABELS, get_label, get_text
from bot.subscription import (
    check_and_consume_disappearing_quota,
    compute_retention_deadline,
    is_disappearing_message,
    resolve_user_plan,
)
from db import MessageCache, Spyusers
from logging_config import register_log_translations

logger = logging.getLogger(__name__)

register_log_translations(
    {
        "Skipping caching for banned user %s": {
            "ru": "Пропускаем кеширование для заблокированного пользователя %s",
        },
        "Owner profile not found for user_id=%s": {
            "ru": "Не найден профиль владельца для user_id=%s",
        },
        "Updated %s message %s-%s": {
            "ru": "Обновлено %s сообщение %s-%s",
        },
        "Cached %s message %s-%s": {
            "ru": "Закэшировано %s сообщение %s-%s",
        },
        "Skipped caching for plan %s (store disabled)": {
            "ru": "Кеширование пропущено для тарифа %s (хранилище отключено)",
        },
        "Error caching message: %s": {
            "ru": "Ошибка при кешировании сообщения: %s",
        },
        "Error handling %s: %s": {
            "ru": "Ошибка обработки %s: %s",
        },
    }
)


@dataclass(frozen=True, slots=True)
class RecentMessage:
    chat_id: int
    message_id: int
    text: str
    user_full_name: str
    message_type: str
    additional_info: str
    user_id: int


_RECENT_CACHE_LIMIT = 512
_recent_messages: "OrderedDict[Tuple[int, int], RecentMessage]" = OrderedDict()


def store_recent_message(entry: RecentMessage) -> None:
    """Keep recent messages in memory for quick access before DB commit."""
    key = (entry.chat_id, entry.message_id)
    if key in _recent_messages:
        _recent_messages.pop(key)
    _recent_messages[key] = entry
    if len(_recent_messages) > _RECENT_CACHE_LIMIT:
        _recent_messages.popitem(last=False)


def get_recent_message(chat_id: int, message_id: int) -> Optional[RecentMessage]:
    """Return cached recent message if available."""
    return _recent_messages.get((chat_id, message_id))


async def _commit_if_needed(session: AsyncSession) -> None:
    """Commit only when a transaction is active to release SQLite locks."""
    if session.in_transaction():
        await session.commit()


def _format_reset_phrase(reset_at: datetime | None, language: str | None) -> str:
    """Return user-friendly reset moment in UTC for limit warnings."""
    lang = (language or DEFAULT_LANGUAGE).lower()
    if reset_at is None:
        return "скоро" if lang == "ru" else "soon"
    return reset_at.strftime("%Y-%m-%d %H:%M UTC")


async def business_text_ch(
    msg: Message,
    bot: Bot,
    types: str,
    uid: int,
    session: AsyncSession,
    caption: str = "None",
    language: str | None = None,
) -> None:
    """Store message in database using SQLAlchemy."""
    try:
        if msg.from_user:
            profile = await session.scalar(
                select(Spyusers).where(Spyusers.user_id == msg.from_user.id)
            )
            if profile and profile.is_banned:
                logger.debug("Skipping caching for banned user %s", msg.from_user.id)
                return

        owner = await session.scalar(
            select(Spyusers).where(Spyusers.user_id == uid)
        )
        if owner is None:
            logger.warning("Owner profile not found for user_id=%s", uid)
            return

        now = datetime.utcnow()
        plan = resolve_user_plan(owner, now)
        effective_language = language or owner.language or DEFAULT_LANGUAGE
        is_disappearing = is_disappearing_message(msg)

        if is_disappearing and types in {"photo", "video", "video_note", "voice"}:
            allowed, reason, limit_value, reset_at = check_and_consume_disappearing_quota(owner, plan, now)
            if not allowed:
                if reason == "not_allowed":
                    warning_text = get_text("subscription_media_not_allowed", effective_language)
                elif reason == "weekly_limit":
                    reset_text = _format_reset_phrase(reset_at, effective_language)
                    warning_text = get_text(
                        "subscription_media_weekly_limit_reached",
                        effective_language,
                        limit=str(limit_value or 0),
                        reset=reset_text,
                    )
                elif reason == "monthly_limit":
                    reset_text = _format_reset_phrase(reset_at, effective_language)
                    warning_text = get_text(
                        "subscription_media_monthly_limit_reached",
                        effective_language,
                        limit=str(limit_value or 0),
                        reset=reset_text,
                    )
                else:
                    warning_text = get_text("subscription_media_not_allowed", effective_language)
                await bot.send_message(
                    uid,
                    warning_text,
                    disable_web_page_preview=True,
                )
                await _commit_if_needed(session)
                return

        await _commit_if_needed(session)

        # Create message cache entry
        message_cache = MessageCache(
            message_id=msg.message_id, # Use original message_id
            chat_id=msg.chat.id,       # Use original chat_id
            user_full_name=(
                (msg.from_user.full_name if msg.from_user else "")
                .encode("utf-8", "ignore")
                .decode("utf-8")
            ),
            user_id=uid
        )
        
        # Handle different message types
        if types == 'text':
            message_cache.text = (msg.text or '').encode('utf-8', 'ignore').decode('utf-8') # Ensure UTF-8
            message_cache.message_type = types
            message_cache.additional_info = (caption or '').encode('utf-8', 'ignore').decode('utf-8') # Ensure UTF-8
            
        elif types == 'photo':
            message_cache.text = msg.photo[-1].file_id
            message_cache.message_type = types
            message_cache.additional_info = (caption or msg.caption or 'None').encode('utf-8', 'ignore').decode('utf-8') # Ensure UTF-8
            
        elif types == 'video':
            message_cache.text = msg.video.file_id
            message_cache.message_type = types
            message_cache.additional_info = (caption or msg.caption or 'None').encode('utf-8', 'ignore').decode('utf-8') # Ensure UTF-8
            
        elif types == 'video_note':
            message_cache.text = msg.video_note.file_id
            message_cache.message_type = types
            message_cache.additional_info = (caption or '').encode('utf-8', 'ignore').decode('utf-8') # Ensure UTF-8
            
        elif types == 'voice':
            message_cache.text = msg.voice.file_id
            message_cache.message_type = types
            message_cache.additional_info = (caption or '').encode('utf-8', 'ignore').decode('utf-8') # Ensure UTF-8
        
        message_cache.expires_at = compute_retention_deadline(plan, now, owner)

        if plan.store_messages:
            existing_message = await session.get(MessageCache, (msg.chat.id, msg.message_id))
            if existing_message:
                existing_message.user_full_name = message_cache.user_full_name
                existing_message.text = message_cache.text
                existing_message.message_type = message_cache.message_type
                existing_message.additional_info = message_cache.additional_info
                existing_message.user_id = message_cache.user_id
                existing_message.expires_at = message_cache.expires_at
                logger.debug(
                    "Updated %s message %s-%s",
                    types,
                    msg.chat.id,
                    msg.message_id,
                )
            else:
                session.add(message_cache)
                logger.debug(
                    "Cached %s message %s-%s",
                    types,
                    msg.chat.id,
                    msg.message_id,
                )
        else:
            logger.debug('Skipped caching for plan %s (store disabled)', plan.key)

        store_recent_message(
            RecentMessage(
                chat_id=msg.chat.id,
                message_id=msg.message_id,
                text=message_cache.text,
                user_full_name=message_cache.user_full_name,
                message_type=message_cache.message_type,
                additional_info=message_cache.additional_info or "none",
                user_id=uid,
            )
        )

        await _commit_if_needed(session)

    except Exception as e:
        logger.exception("Error caching message: %s", e)
        if session.in_transaction():
            await session.rollback()


async def handle_media(
    msg,
    file_type: str,
    media_path: str,
    media_caption: str,
    media_method,
    connection,
    bot,
    language: str | None,
    session: AsyncSession,
) -> None:
    """Process and save media files from messages."""
    try:
        media = getattr(msg.reply_to_message, file_type)
        bot_name = await bot.get_me()
        caption_text = get_text("media_saved_caption", language, bot_username=bot_name.username or "")

        owner = await session.scalar(
            select(Spyusers).where(Spyusers.user_id == connection.user.id)
        )
        now = datetime.utcnow()
        plan = None
        plan_language = language or DEFAULT_LANGUAGE
        reply_is_disappearing = False
        if owner is not None:
            plan = resolve_user_plan(owner, now)
            plan_language = language or owner.language or DEFAULT_LANGUAGE
            reply_is_disappearing = is_disappearing_message(msg.reply_to_message)
            if reply_is_disappearing and not plan.allow_disappearing_media:
                warning_text = get_text("subscription_media_not_allowed", plan_language)
                await bot.send_message(
                    connection.user.id,
                    warning_text,
                    disable_web_page_preview=True,
                )
                await _commit_if_needed(session)
                return
            if reply_is_disappearing:
                allowed, reason, limit_value, reset_at = check_and_consume_disappearing_quota(owner, plan, now)
                if not allowed:
                    if reason == "weekly_limit":
                        reset_text = _format_reset_phrase(reset_at, plan_language)
                        warning_text = get_text(
                            "subscription_media_weekly_limit_reached",
                            plan_language,
                            limit=str(limit_value or 0),
                            reset=reset_text,
                        )
                    elif reason == "monthly_limit":
                        reset_text = _format_reset_phrase(reset_at, plan_language)
                        warning_text = get_text(
                            "subscription_media_monthly_limit_reached",
                            plan_language,
                            limit=str(limit_value or 0),
                            reset=reset_text,
                        )
                    else:
                        warning_text = get_text("subscription_media_not_allowed", plan_language)
                    await bot.send_message(
                        connection.user.id,
                        warning_text,
                        disable_web_page_preview=True,
                    )
                    await _commit_if_needed(session)
                    return
            await _commit_if_needed(session)

        if isinstance(media, list):
            media_file = media[-1]  # Get highest quality
        else:
            media_file = media
            
        file_id = media_file.file_id
        file = await bot.get_file(file_id)
        check = file.file_id[0:2]

        md = ['GA', 'Fg', 'Fw', 'GQ']
        requires_quota = reply_is_disappearing or (check in md)

        if owner is not None and plan is not None and requires_quota:
            if not plan.allow_disappearing_media:
                warning_text = get_text("subscription_media_not_allowed", plan_language)
                await bot.send_message(
                    connection.user.id,
                    warning_text,
                    disable_web_page_preview=True,
                )
                await _commit_if_needed(session)
                return
            allowed, reason, limit_value, reset_at = check_and_consume_disappearing_quota(owner, plan, now)
            if not allowed:
                if reason == "weekly_limit":
                    reset_text = _format_reset_phrase(reset_at, plan_language)
                    warning_text = get_text(
                        "subscription_media_weekly_limit_reached",
                        plan_language,
                        limit=str(limit_value or 0),
                        reset=reset_text,
                    )
                elif reason == "monthly_limit":
                    reset_text = _format_reset_phrase(reset_at, plan_language)
                    warning_text = get_text(
                        "subscription_media_monthly_limit_reached",
                        plan_language,
                        limit=str(limit_value or 0),
                        reset=reset_text,
                    )
                else:
                    warning_text = get_text("subscription_media_not_allowed", plan_language)
                await bot.send_message(
                    connection.user.id,
                    warning_text,
                    disable_web_page_preview=True,
                )
                await _commit_if_needed(session)
                return
            await _commit_if_needed(session)

        if check in md:
            # Create directory if it doesn't exist
            if not os.path.exists(media_path):
                os.makedirs(media_path)
                
            local_file_path = f"{media_path}/{file.file_path.split('/')[-1]}"
            await bot.download_file(file.file_path, local_file_path)

            # Create FSInputFile for uploading
            media_file_input = FSInputFile(local_file_path)  # Renamed to avoid conflict

            # Send appropriate media type
            if file_type == 'photo':
                await media_method(connection.user.id, photo=media_file_input, caption=caption_text, parse_mode='HTML')
            elif file_type == 'video':
                await media_method(connection.user.id, video=media_file_input, caption=caption_text, parse_mode='HTML')
            elif file_type == 'voice':
                await media_method(connection.user.id, voice=media_file_input, caption=caption_text, parse_mode='HTML')
            elif file_type == 'video_note': # Corrected to video_note
                await bot.send_video_note(connection.user.id, video_note=media_file_input)
            # Clean up
            os.remove(local_file_path)
            await asyncio.sleep(0.05)

        
    except Exception as e:
        logger.exception("Error handling %s: %s", file_type, e)
        media_type_label = get_label(MEDIA_TYPE_LABELS, file_type, language)
        await bot.send_message(
            connection.user.id,
            get_text("media_error_processing", language, media_type=media_type_label),
        )
