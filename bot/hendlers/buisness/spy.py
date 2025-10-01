import asyncio
import logging

from aiogram import Bot, Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils import business_text_ch, handle_media
from logging_config import register_log_translations

register_log_translations(
    {
        "Error handling business text: %s": {
            "ru": "Ошибка обработки бизнес-сообщения (текст): %s",
        },
        "Error handling business photo: %s": {
            "ru": "Ошибка обработки бизнес-сообщения (фото): %s",
        },
        "Error handling business video: %s": {
            "ru": "Ошибка обработки бизнес-сообщения (видео): %s",
        },
        "Error handling business video note: %s": {
            "ru": "Ошибка обработки бизнес-сообщения (видеосообщение): %s",
        },
        "Error handling business voice: %s": {
            "ru": "Ошибка обработки бизнес-сообщения (голос): %s",
        },
    }
)

# Configure logger
def spy_router() -> Router:
    logger = logging.getLogger(__name__)
    router = Router()

    # ==================== MESSAGE HANDLERS ====================

    @router.business_message(F.text)
    async def business_text_handler(msg: Message, bot: Bot, session: AsyncSession, language: str) -> None:
        """Handle text messages in business chats."""
        try:
            feedback = msg.business_connection_id
            connection = await bot.get_business_connection(feedback)

            # Different handling for replies vs direct messages
            if not msg.reply_to_message:
                # Direct message
                await business_text_ch(
                    msg=msg,
                    bot=bot,
                    types='text',
                    caption='None',
                    uid=connection.user.id,
                    session=session,
                    language=language,
                )
            else:
                # Reply to a message
                user_connection = await bot.get_business_connection(feedback)

                # Check if the user is replying to their own message
                if msg.from_user.id == user_connection.user.id:
                    # Handle different types of replied media
                    if msg.reply_to_message.photo:
                        await handle_media(msg, "photo", "photos", "Photo", bot.send_photo, user_connection, bot, language, session)
                    elif msg.reply_to_message.video:
                        await handle_media(msg, "video", "videos", "Video", bot.send_video, user_connection, bot, language, session)
                    elif msg.reply_to_message.video_note:
                        await handle_media(msg, "video_note", "videos", "Video note", bot.send_video, user_connection, bot, language, session)
                    elif msg.reply_to_message.voice:
                        await handle_media(msg, "voice", "videos", "Voice", bot.send_voice, user_connection, bot, language, session)
                    else:
                        await business_text_ch(
                            msg=msg,
                            bot=bot,
                            types='text',
                            caption='None',
                            uid=user_connection.user.id,
                            session=session,
                            language=language,
                        )
                else:
                    # Handle reply from someone else
                    await business_text_ch(
                        msg=msg,
                        bot=bot,
                        types='text',
                        caption='None',
                        uid=user_connection.user.id,
                        session=session,
                        language=language,
                    )
        except Exception as e:
            logger.exception("Error handling business text: %s", e)


    @router.business_message(F.photo)
    async def business_photo_handler(msg: Message, bot: Bot, session: AsyncSession, language: str) -> None:
        """Handle photo messages in business chats."""
        try:
            feedback = msg.business_connection_id
            connection = await bot.get_business_connection(feedback)

            await business_text_ch(
                msg=msg,
                bot=bot,
                types='photo',
                caption=msg.caption,
                uid=connection.user.id,
                session=session,
                language=language,
            )

        except Exception as e:
            logger.exception("Error handling business photo: %s", e)


    @router.business_message(F.video)
    async def business_video_handler(msg: Message, bot: Bot, session: AsyncSession, language: str) -> None:
        """Handle video messages in business chats."""
        try:
            feedback = msg.business_connection_id
            connection = await bot.get_business_connection(feedback)

            await business_text_ch(
                msg=msg,
                bot=bot,
                types='video',
                caption=msg.caption,
                uid=connection.user.id,
                session=session,
                language=language,
            )

        except Exception as e:
            logger.exception("Error handling business video: %s", e)


    @router.business_message(F.video_note)
    async def business_video_note_handler(msg: Message, bot: Bot, session: AsyncSession, language: str) -> None:
        """Handle video note messages in business chats."""
        try:
            feedback = msg.business_connection_id
            connection = await bot.get_business_connection(feedback)

            await business_text_ch(
                msg=msg,
                bot=bot,
                types='video_note',
                caption=msg.caption,
                uid=connection.user.id,
                session=session,
                language=language,
            )

        except Exception as e:
            logger.exception("Error handling business video note: %s", e)


    @router.business_message(F.voice)
    async def business_voice_handler(msg: Message, bot: Bot, session: AsyncSession, language: str) -> None:
        """Handle voice messages in business chats."""
        try:
            feedback = msg.business_connection_id
            connection = await bot.get_business_connection(feedback)

            await business_text_ch(
                msg=msg,
                bot=bot,
                types='voice',
                caption=msg.caption,
                uid=connection.user.id,
                session=session,
                language=language,
            )

        except Exception as e:
            logger.exception("Error handling business voice: %s", e)

    return router
