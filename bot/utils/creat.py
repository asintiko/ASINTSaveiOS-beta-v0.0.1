import logging
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.localization import get_text
from db import Webhook, Spyusers
from config import OTHER_BOTS_URL
from logging_config import register_log_translations

logger = logging.getLogger(__name__)

register_log_translations(
    {
        "Adding bot with token: %s...%s": {
            "ru": "Добавление бота с токеном: %s...%s",
        },
        "Successfully authenticated bot: @%s (ID: %s)": {
            "ru": "Бот успешно авторизован: @%s (ID: %s)",
        },
        "Invalid token provided: %s...%s": {
            "ru": "Указан неверный токен: %s...%s",
        },
        "Deleted existing webhook for @%s": {
            "ru": "Удалён существующий webhook для @%s",
        },
        "Setting webhook for @%s to %s": {
            "ru": "Устанавливаем webhook для @%s: %s",
        },
        "Webhook successfully set for @%s: %s": {
            "ru": "Webhook для @%s успешно установлен: %s",
        },
        "Webhook for @%s saved to database": {
            "ru": "Webhook для @%s сохранён в базе данных",
        },
        "Database error saving webhook: %s": {
            "ru": "Ошибка базы данных при сохранении webhook: %s",
        },
        "Failed to set webhook for @%s": {
            "ru": "Не удалось установить webhook для @%s",
        },
        "Error adding bot: %s": {
            "ru": "Ошибка при добавлении бота: %s",
        },
    }
)

async def command_add_bot(
    message: Message,
    bot: Bot,
    token: str,
    session: AsyncSession | None = None,
    language: str | None = None,
) -> Any:
    try:
        logger.info("Adding bot with token: %s...%s", token[:5], token[-5:])

        if session:
            existing_user = await session.scalar(
                select(Spyusers).where(Spyusers.user_id == message.from_user.id)
            )
            if existing_user and existing_user.is_banned:
                return await message.answer(get_text("add_bot_account_banned", language))

            existing_token = await session.scalars(select(Webhook).where(Webhook.token == token))
            if existing_token.first():
                return await message.answer(get_text("add_bot_token_exists", language))

        new_bot = Bot(token=token, session=bot.session)
        try:
            bot_user = await new_bot.get_me()
            logger.info(
                "Successfully authenticated bot: @%s (ID: %s)",
                bot_user.username,
                bot_user.id,
            )
        except TelegramUnauthorizedError:
            logger.warning("Invalid token provided: %s...%s", token[:5], token[-5:])
            return await message.answer(get_text("add_bot_invalid_api_token", language))

        await new_bot.delete_webhook(drop_pending_updates=True)
        logger.info("Deleted existing webhook for @%s", bot_user.username)

        webhook_url = OTHER_BOTS_URL.format(bot_token=token)
        logger.info("Setting webhook for @%s to %s", bot_user.username, webhook_url)

        allowed_updates = [
            "message",
            "edited_message",
            "callback_query",
            "business_message",
            "edited_business_message",
            "deleted_business_messages",
        ]

        await new_bot.set_webhook(webhook_url, allowed_updates=allowed_updates)

        webhook_info = await new_bot.get_webhook_info()
        if webhook_info.url:
            logger.info(
                "Webhook successfully set for @%s: %s",
                bot_user.username,
                webhook_info.url,
            )

            if session:
                try:
                    new_webhook = Webhook(
                        bot_id=bot_user.id,
                        bot_username=bot_user.username,
                        webhook_url=webhook_url,
                        token=token,
                    )
                    session.add(new_webhook)
                    await session.commit()
                    logger.info("Webhook for @%s saved to database", bot_user.username)
                except Exception as db_error:
                    logger.error("Database error saving webhook: %s", db_error)
                    await session.rollback()

            return await message.answer(
                get_text(
                    "add_bot_success",
                    language,
                    username=bot_user.username or "",
                )
            )

        logger.error("Failed to set webhook for @%s", bot_user.username)
        return await message.answer(
            get_text(
                "add_bot_webhook_failed",
                language,
                username=bot_user.username or "",
            )
        )

    except Exception as exc:
        logger.exception("Error adding bot: %s", exc)
        return await message.answer(get_text("add_bot_error", language, error=str(exc)))
