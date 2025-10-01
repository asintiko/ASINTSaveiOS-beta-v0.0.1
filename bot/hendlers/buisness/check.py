import logging
import typing
import time
import asyncio
from html import escape
from datetime import datetime

from aiogram import Router, Bot, F
from aiogram.types import Message
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db import MessageCache, Spyusers
from bot.utils import RecentMessage, get_recent_message, store_recent_message
from bot.localization import BUSINESS_ITEM_NAMES, DEFAULT_LANGUAGE, get_label, get_text
from bot.subscription import check_notification_quota, resolve_user_plan
from logging_config import register_log_translations

register_log_translations(
    {
        "Failed to send notification quota warning to %s": {
            "ru": "Не удалось отправить предупреждение о лимите уведомлений пользователю %s",
        },
        "Unable to fetch chat info for %s: %s": {
            "ru": "Не удалось получить информацию о чате %s: %s",
        },
        "No cached data for deleted message chat=%s message=%s": {
            "ru": "Нет кешированных данных для удалённого сообщения chat=%s message=%s",
        },
        "Notification sent for deleted %s message %s": {
            "ru": "Отправлено уведомление об удалённом сообщении типа %s %s",
        },
        "Error checking deleted message: %s": {
            "ru": "Ошибка при проверке удалённого сообщения: %s",
        },
        "Error handling edited message: %s": {
            "ru": "Ошибка при обработке изменённого сообщения: %s",
        },
        "Error handling deleted messages: %s": {
            "ru": "Ошибка при обработке удалённых сообщений: %s",
        },
    }
)

# Configure logger


def _format_reset_phrase(reset_at: datetime | None, language: str | None) -> str:
    lang = (language or DEFAULT_LANGUAGE).lower()
    if reset_at is None:
        return "скоро" if lang == "ru" else "soon"
    return reset_at.strftime("%Y-%m-%d %H:%M UTC")


def check_router() -> Router:
    logger = logging.getLogger(__name__)
    router = Router(name=__name__)

    # Define message action constants
    ACTION_EDIT = "edit"
    ACTION_DELETE = "delete"

    class RecentsItem(typing.NamedTuple):
        """Store information about recent message changes."""
        timestamp: int
        chat_id: int
        message_id: int
        action: str
        old_text: typing.Optional[str] = None
        new_text: typing.Optional[str] = None

        @classmethod
        def from_edit(cls, message: Message, old_text: str) -> "RecentsItem":
            return cls(
                timestamp=int(time.time()),
                chat_id=message.chat.id,
                message_id=message.message_id,
                action=ACTION_EDIT,
                old_text=old_text,
                new_text=message.text,
            )



    async def _ensure_notification_quota(
        *,
        session: AsyncSession,
        bot: Bot,
        user_id: int,
        language: str,
    ) -> bool:
        profile = await session.scalar(select(Spyusers).where(Spyusers.user_id == user_id))
        if profile is None:
            return True

        now = datetime.utcnow()
        plan = resolve_user_plan(profile, now)
        allowed, reason, limit_value, reset_at = check_notification_quota(profile, plan, now)
        await session.flush()
        if allowed:
            return True

        if reason == "weekly_limit":
            warning_key = "subscription_notification_weekly_limit_reached"
        elif reason == "monthly_limit":
            warning_key = "subscription_notification_monthly_limit_reached"
        else:
            warning_key = "subscription_notification_weekly_limit_reached"

        reset_text = _format_reset_phrase(reset_at, language)
        warning_text = get_text(
            warning_key,
            language or DEFAULT_LANGUAGE,
            limit=str(limit_value or 0),
            reset=reset_text,
        )
        try:
            await bot.send_message(
                user_id,
                warning_text,
                disable_web_page_preview=True,
            )
        except Exception:
            logger.debug("Failed to send notification quota warning to %s", user_id, exc_info=True)
        return False


    def _build_user_link(
        user_id: int,
        display_name: str,
        username: str | None = None,
    ) -> str:
        safe_name = display_name.strip() or f"User {user_id}"
        if username:
            return f'<a href="https://t.me/{username}">{safe_name}</a>'
        return f'<a href="tg://user?id={user_id}">{safe_name}</a>'

    async def _format_sender_reference(
        *,
        bot: Bot,
        chat_id: int,
        display_name: str | None,
        language: str,
        message_id: int,
    ) -> str:
        escaped_name = escape(display_name or "")
        if chat_id > 0:
            link_text = escaped_name.strip() or f"User {chat_id}"
            username: str | None = None
            try:
                chat = await bot.get_chat(chat_id)
            except Exception:
                chat = None
            if chat is not None:
                username = getattr(chat, "username", None)
                if not link_text.strip():
                    link_text = escape(
                        getattr(chat, "full_name", None)
                        or getattr(chat, "first_name", None)
                        or ""
                    )
            return _build_user_link(chat_id, link_text, username)

        chat_title = escaped_name
        chat_link: str | None = None

        try:
            chat = await bot.get_chat(chat_id)
        except Exception as exc:
            logger.debug("Unable to fetch chat info for %s: %s", chat_id, exc)
            chat = None
        else:
            raw_title = chat.title or getattr(chat, "full_name", None) or chat.username or display_name
            chat_title = escape(raw_title or "")
            if chat.username:
                chat_link = f"https://t.me/{chat.username}/{message_id}"
            else:
                chat_id_str = str(chat_id)
                if chat_id_str.startswith("-100"):
                    chat_link = f"https://t.me/c/{chat_id_str[4:]}/{message_id}"

        link_text = chat_title.strip() or f"Chat {abs(chat_id)}"
        if chat_link:
            return f'<a href="{chat_link}">{link_text}</a>'

        fallback = link_text or get_text("business_unknown_sender", language)
        if not fallback.strip():
            fallback = get_text("business_unknown_sender", language)
        if chat_id < 0:
            fallback += get_text("business_sender_chat_suffix", language, chat_id=chat_id)
        return fallback

    async def _resolve_user_language(
        session: AsyncSession,
        user_id: int,
        fallback_language: str | None,
    ) -> str:
        base_language = (fallback_language or DEFAULT_LANGUAGE)
        profile = await session.scalar(select(Spyusers).where(Spyusers.user_id == user_id))
        if profile and profile.language:
            return profile.language
        return base_language

    async def check_message(
        chat_id: int,
        original_message_id: int,
        bot: Bot,
        session: AsyncSession,
        language: str | None,
    ) -> None:
        """Check if a deleted message exists in cache, notify user, and delete it."""
        try:
            stmt = select(MessageCache).where(
                MessageCache.chat_id == chat_id,
                MessageCache.message_id == original_message_id,
            )
            cached_message = await session.scalar(stmt)
            recent_message = get_recent_message(chat_id, original_message_id)

            if not cached_message and not recent_message:
                logger.debug(
                    "No cached data for deleted message chat=%s message=%s",
                    chat_id,
                    original_message_id,
                )
                return

            if cached_message:
                user_id_to_notify = cached_message.user_id
                original_sender_chat_id = cached_message.chat_id
                original_sender_name = cached_message.user_full_name
                message_content = cached_message.text
                msg_type = cached_message.message_type or "text"
                caption_from_cache = cached_message.additional_info
                await session.delete(cached_message)
            else:
                user_id_to_notify = recent_message.user_id
                original_sender_chat_id = recent_message.chat_id
                original_sender_name = recent_message.user_full_name
                message_content = recent_message.text
                msg_type = recent_message.message_type or "text"
                caption_from_cache = recent_message.additional_info

            target_language = await _resolve_user_language(
                session=session,
                user_id=user_id_to_notify,
                fallback_language=language,
            )

            notification_allowed = await _ensure_notification_quota(
                session=session,
                bot=bot,
                user_id=user_id_to_notify,
                language=target_language,
            )
            if not notification_allowed:
                return

            sender_link = await _format_sender_reference(
                bot=bot,
                chat_id=original_sender_chat_id,
                display_name=original_sender_name,
                language=target_language,
                message_id=original_message_id,
            )

            label_sender = get_text("business_label_sender", target_language)
            sender_block = get_text(
                "business_sender_block",
                target_language,
                label=label_sender,
                sender=sender_link,
            )

            caption_detail_value = ""
            if caption_from_cache:
                normalized_caption = caption_from_cache.strip()
                if normalized_caption and normalized_caption.lower() != "none":
                    caption_detail_value = escape(normalized_caption)

            def render_text_section(label: str, value: str) -> str:
                safe_value = value.strip() if value else ""
                safe_value = safe_value or "—"
                return f"<blockquote><i>{label}: {safe_value}</i></blockquote>\n"

            label_text = get_text("business_label_text", target_language)
            item_name = get_label(BUSINESS_ITEM_NAMES, msg_type, target_language)
            deleted_title = get_text(
                "business_deleted_title",
                target_language,
                item=item_name,
            )

            if msg_type == "text":
                text_content_escaped = escape(message_content or "")
                notification_text = (
                    f"{deleted_title}{sender_block}"
                    f"{render_text_section(label_text, text_content_escaped)}"
                )
                await bot.send_message(
                    user_id_to_notify,
                    text=notification_text.strip(),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            elif msg_type == "photo":
                final_caption = f"{deleted_title}{sender_block}"
                if caption_detail_value:
                    final_caption += render_text_section(
                        label_text,
                        caption_detail_value,
                    )
                await bot.send_photo(
                    user_id_to_notify,
                    photo=message_content,
                    caption=final_caption.strip(),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            elif msg_type == "video":
                final_caption = f"{deleted_title}{sender_block}"
                if caption_detail_value:
                    final_caption += render_text_section(
                        label_text,
                        caption_detail_value,
                    )
                await bot.send_video(
                    user_id_to_notify,
                    video=message_content,
                    caption=final_caption.strip(),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            elif msg_type == "video_note":
                await bot.send_video_note(user_id_to_notify, video_note=message_content)
                text_for_video_note = f"{deleted_title}{sender_block}"
                if caption_detail_value:
                    text_for_video_note += render_text_section(
                        label_text,
                        caption_detail_value,
                    )
                await bot.send_message(
                    user_id_to_notify,
                    text=text_for_video_note.strip(),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            elif msg_type == "voice":
                final_caption = f"{deleted_title}{sender_block}"
                if caption_detail_value:
                    final_caption += render_text_section(
                        label_text,
                        caption_detail_value,
                    )
                await bot.send_voice(
                    user_id_to_notify,
                    voice=message_content,
                    caption=final_caption.strip(),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )

            await asyncio.sleep(0.05)
            logger.info(
                "Notification sent for deleted %s message %s",
                msg_type,
                original_message_id,
            )

        except Exception as exc:
            logger.exception("Error checking deleted message: %s", exc)

    @router.edited_business_message(F.text)
    async def business_edit(message: Message, bot: Bot, session: AsyncSession, language: str) -> None:
        try:
            feedback = message.business_connection_id
            connection = await bot.get_business_connection(feedback)

            stmt = select(MessageCache).where(
                MessageCache.chat_id == message.chat.id,
                MessageCache.message_id == message.message_id,
            )
            cached_message = await session.scalar(stmt)
            recent_message = get_recent_message(message.chat.id, message.message_id)

            editor_user_id = message.from_user.id
            editor_full_name = (
                message.from_user.full_name
                if message.from_user
                else get_text("business_unknown_user", language)
            )
            editor_full_name_html = escape(editor_full_name or "")
            link_text_editor = (
                editor_full_name_html if editor_full_name_html.strip() else str(editor_user_id)
            )
            editor_user_link = _build_user_link(
                editor_user_id,
                link_text_editor,
                getattr(message.from_user, "username", None) if message.from_user else None,
            )

            owner_user_id = connection.user.id
            message_type_cached = "text"
            additional_info_cached = "none"
            user_full_name_cached = editor_full_name
            old_text = ""
            previous_found = False

            if cached_message:
                old_text = cached_message.text or ""
                previous_found = True
                owner_user_id = cached_message.user_id
                message_type_cached = cached_message.message_type or "text"
                additional_info_cached = cached_message.additional_info or "none"
                user_full_name_cached = cached_message.user_full_name or editor_full_name
            elif recent_message:
                old_text = recent_message.text or ""
                previous_found = True
                owner_user_id = recent_message.user_id
                message_type_cached = recent_message.message_type or "text"
                additional_info_cached = recent_message.additional_info or "none"
                user_full_name_cached = recent_message.user_full_name or editor_full_name
                cached_message = MessageCache(
                    message_id=message.message_id,
                    chat_id=message.chat.id,
                    user_full_name=recent_message.user_full_name,
                    text=recent_message.text,
                    message_type=recent_message.message_type,
                    additional_info=recent_message.additional_info,
                    user_id=recent_message.user_id,
                )
                session.add(cached_message)
            else:
                cached_message = MessageCache(
                    message_id=message.message_id,
                    chat_id=message.chat.id,
                    user_full_name=editor_full_name,
                    text="",
                    message_type="text",
                    additional_info="none",
                    user_id=owner_user_id,
                )
                session.add(cached_message)

            new_text = message.text or ""
            cached_message.text = new_text
            cached_message.user_full_name = user_full_name_cached
            cached_message.message_type = message_type_cached
            cached_message.additional_info = additional_info_cached
            cached_message.user_id = owner_user_id

            store_recent_message(
                RecentMessage(
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                    text=new_text,
                    user_full_name=user_full_name_cached,
                    message_type=message_type_cached,
                    additional_info=additional_info_cached,
                    user_id=owner_user_id,
                )
            )

            await session.flush()

            if editor_user_id == connection.user.id:
                return

            target_language = await _resolve_user_language(
                session=session,
                user_id=connection.user.id,
                fallback_language=language,
            )

            notification_allowed = await _ensure_notification_quota(
                session=session,
                bot=bot,
                user_id=connection.user.id,
                language=target_language,
            )
            if not notification_allowed:
                return

            chat_reference = await _format_sender_reference(
                bot=bot,
                chat_id=message.chat.id,
                display_name=getattr(message.chat, "title", None) or getattr(message.chat, "full_name", None),
                language=target_language,
                message_id=message.message_id,
            )

            edit_title = get_text("business_edit_title", target_language)
            edit_user_line = ""
            edit_chat_line = get_text("business_edit_chat", target_language, chat=chat_reference)

            if previous_found:
                old_summary_html = escape(old_text) or "—"
                new_summary_html = escape(new_text) or "—"
                was_value = old_summary_html
                became_value = new_summary_html
                changes_value = f"<s>{old_summary_html}</s> -> {new_summary_html}"
            else:
                new_summary_html = escape(new_text) or "—"
                previous_missing = get_text("business_edit_previous_missing", target_language)
                was_value = previous_missing
                became_value = new_summary_html
                changes_value = new_summary_html

            edit_was_line = get_text("business_edit_was", target_language, value=was_value)
            edit_became_line = get_text("business_edit_became", target_language, value=became_value)
            edit_changes_line = get_text("business_edit_changes", target_language, value=changes_value)

            notification_text = (
                f"{edit_title}"
                f"{edit_user_line}"
                f"{edit_chat_line}"
                f"{edit_was_line}"
                f"{edit_became_line}"
                f"{edit_changes_line}"
            )

            await bot.send_message(
                connection.user.id,
                text=notification_text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            await asyncio.sleep(0.05)
        except Exception as exc:
            logger.exception("Error handling edited message: %s", exc)
    @router.deleted_business_messages()
    async def business_delete(msg: Message, bot: Bot, session: AsyncSession, language: str | None = None) -> None:
        try:
            for message_id_in_list in msg.message_ids:
                full_msg_id = int(f"{msg.chat.id}{message_id_in_list}")
                await check_message(
                    chat_id=msg.chat.id,
                    original_message_id=message_id_in_list,
                    bot=bot,
                    session=session,
                    language=language or DEFAULT_LANGUAGE,
                )
        except Exception as e:
            logger.exception("Error handling deleted messages: %s", e)

    return router
