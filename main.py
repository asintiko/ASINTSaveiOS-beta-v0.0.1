"""
MarkovkaSaveBOT - Telegram бот для сохранения и управления медиа-файлами
Создатель: KulacodmYT.t.me
"""

import argparse
import asyncio
import logging
import sys
import os  # Added for os.remove
import aiohttp  # Ensure this is imported if used by AiohttpSession implicitly or directly
from aiohttp import web
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from logging_config import (
    available_log_languages,
    get_default_log_language,
    register_log_translations,
    setup_logging,
)

from config import (
    TOKEN,
    DATABASE_URL,
    RUN_VIA_POLLING,
    RESET_DB_ON_START,
    BASE_URL,
    MAIN_BOT_PATH,
    WEB_SERVER_HOST,
    WEB_SERVER_PORT,
    OTHER_BOTS_PATH,
    OTHER_BOTS_URL,
    LOG_LANGUAGE,
)

register_log_translations(
    {
        "Bot starting up in POLLING mode...": {
            "ru": "Бот запускается в режиме long polling...",
        },
        "Removed existing database file: %s": {
            "ru": "Удалён существующий файл базы данных: %s",
        },
        "Error removing database file %s: %s": {
            "ru": "Ошибка при удалении файла базы данных %s: %s",
        },
        "Bot authorized as @%s (ID: %s)": {
            "ru": "Бот авторизован как @%s (ID: %s)",
        },
        "Database tables created/ensured.": {
            "ru": "Таблицы базы данных созданы или проверены.",
        },
        "Shutting down (polling mode), closing database connections...": {
            "ru": "Завершение работы (polling): закрываем соединения с базой данных...",
        },
        "Database connections closed.": {
            "ru": "Соединения с базой данных закрыты.",
        },
        "Bot starting up in WEBHOOK mode...": {
            "ru": "Бот запускается в режиме webhook...",
        },
        "Setting webhook to: %s": {
            "ru": "Устанавливаем webhook: %s",
        },
        "Shutting down (webhook mode)...": {
            "ru": "Завершение работы (webhook)...",
        },
        "Webhook deleted": {
            "ru": "Webhook удалён",
        },
        "Starting polling...": {
            "ru": "Запуск long polling...",
        },
        "Polling finished or interrupted. Closing bot session.": {
            "ru": "Опрос завершён или прерван. Закрываем сессию бота.",
        },
        "Starting web server on %s:%s": {
            "ru": "Запуск веб-сервера на %s:%s",
        },
        "Attempting to run in POLLING mode.": {
            "ru": "Пробуем запустить бота в режиме long polling.",
        },
        "Attempting to run in WEBHOOK mode.": {
            "ru": "Пробуем запустить бота в режиме webhook.",
        },
        "BASE_URL is not configured correctly for webhook mode. Please set it in .env. Exiting.": {
            "ru": "BASE_URL настроен некорректно для режима webhook. Укажите значение в .env. Выходим.",
        },
        "MAIN_BOT_PATH is not configured. Please set it in .env. Exiting.": {
            "ru": "MAIN_BOT_PATH не задан. Укажите его в .env. Выходим.",
        },
    }
)

logger = logging.getLogger(__name__)


def _normalize_log_language(candidate: str | None) -> str:
    """Validate and normalize a log language candidate."""

    available = {lang.lower() for lang in available_log_languages()}
    if candidate:
        normalized = candidate.strip().lower()
        if normalized in available:
            return normalized
    return get_default_log_language()


def configure_logging(*, language: str | None = None, level: str | int | None = logging.DEBUG) -> str:
    """Set up logging once per process and return the active language."""

    effective_language = _normalize_log_language(language or LOG_LANGUAGE)
    setup_logging(level=level, language=effective_language)
    return effective_language


def parse_cli_args(argv: list[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
    """Parse and return known CLI arguments plus unhandled extras."""

    parser = argparse.ArgumentParser(description="Run the SaveMod Telegram bot")
    parser.add_argument(
        "--log-language",
        dest="log_language",
        choices=available_log_languages(),
        metavar="LANG",
        help="Override log language (default from .env)",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        metavar="LEVEL",
        help="Override base log level (name or number)",
    )
    return parser.parse_known_args(argv)


# Configure logging immediately for library consumers; main block may override later.
configure_logging(language=LOG_LANGUAGE, level=logging.DEBUG)

from aiogram import Bot, Dispatcher
from aiogram.types import Update

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from bot.hendlers import setup_routers # Assuming this sets up all command and message handlers
# from bot.callback import call_router # If callbacks are separate, include its router
from bot.middlewares import DbSessionMiddleware, OnboardingMiddleware # Assuming this exists

from db import Base # Assuming this exists

# Function to get DB path from DATABASE_URL
def get_db_path(db_url):
    if db_url.startswith("sqlite+aiosqlite:///./"):
        return db_url[len("sqlite+aiosqlite:///./"):]
    elif db_url.startswith("sqlite+aiosqlite:///"):
        # Absolute path, but os.remove should handle it
        return db_url[len("sqlite+aiosqlite:///"):] 
    return None

_USING_SQLITE = DATABASE_URL.startswith("sqlite+aiosqlite")

_engine_kwargs: dict[str, object] = {}
if _USING_SQLITE:
    _engine_kwargs["connect_args"] = {"timeout": 30}
    _engine_kwargs["poolclass"] = NullPool

_engine = create_async_engine(DATABASE_URL, **_engine_kwargs)
_sessionmaker = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


def _apply_sqlite_pragmas(sync_conn) -> None:
    """Enable WAL mode and generous timeouts for concurrent SQLite access."""
    sync_conn.exec_driver_sql("PRAGMA journal_mode=WAL")
    sync_conn.exec_driver_sql("PRAGMA synchronous=NORMAL")
    sync_conn.exec_driver_sql("PRAGMA busy_timeout=30000")


async def on_startup_polling(bot: Bot):
    logger.info("Bot starting up in POLLING mode...")
    if RESET_DB_ON_START:
        db_path = get_db_path(DATABASE_URL)
        if db_path and os.path.exists(db_path):
            try:
                os.remove(db_path)
                logger.info("Removed existing database file: %s", db_path)
            except OSError as e:
                logger.error("Error removing database file %s: %s", db_path, e)

    bot_info = await bot.get_me()
    logger.info("Bot authorized as @%s (ID: %s)", bot_info.username, bot_info.id)
    async with _engine.begin() as conn:
        if _USING_SQLITE:
            await conn.run_sync(_apply_sqlite_pragmas)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/ensured.")

async def on_shutdown_polling():
    logger.info("Shutting down (polling mode), closing database connections...")
    await _engine.dispose()
    logger.info("Database connections closed.")

# Webhook startup/shutdown functions would need similar refactoring if used
async def on_startup_webhook(bot: Bot): # Changed to accept bot
    logger.info("Bot starting up in WEBHOOK mode...")
    if RESET_DB_ON_START:
        db_path = get_db_path(DATABASE_URL)
        if db_path and os.path.exists(db_path):
            try:
                os.remove(db_path)
                logger.info("Removed existing database file: %s", db_path)
            except OSError as e:
                logger.error("Error removing database file %s: %s", db_path, e)

    webhook_url = f"{BASE_URL}{MAIN_BOT_PATH}"
    logger.info("Setting webhook to: %s", webhook_url)
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(webhook_url, allowed_updates=Update.model_fields.keys())
    bot_info = await bot.get_me()
    logger.info("Bot authorized as @%s (ID: %s)", bot_info.username, bot_info.id)
    async with _engine.begin() as conn:
        if _USING_SQLITE:
            await conn.run_sync(_apply_sqlite_pragmas)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/ensured.")
    # register_webhook_urls(app) # Mirror bot logic needs review

async def on_shutdown_webhook(bot: Bot): # Changed to accept bot
    logger.info("Shutting down (webhook mode)...")
    if bot:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted")
    await _engine.dispose()
    logger.info("Database connections closed.")

async def main_polling():
    session = AiohttpSession()
    # Create bot instance locally
    local_bot = Bot(token=TOKEN, session=session)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.workflow_data["sessionmaker"] = _sessionmaker

    # Register startup/shutdown handlers
    dp.startup.register(on_startup_polling)
    dp.shutdown.register(on_shutdown_polling)

    # Middlewares
    db_middleware = DbSessionMiddleware(_sessionmaker)
    onboarding_middleware = OnboardingMiddleware()

    dp.message.middleware(db_middleware)
    dp.message.middleware(onboarding_middleware)

    dp.business_message.middleware(db_middleware)
    dp.business_message.middleware(onboarding_middleware)

    dp.deleted_business_messages.middleware(db_middleware)
    dp.deleted_business_messages.middleware(onboarding_middleware)
    dp.edited_business_message.middleware(db_middleware)
    dp.edited_business_message.middleware(onboarding_middleware)
    dp.callback_query.middleware(db_middleware)
    dp.callback_query.middleware(onboarding_middleware)

    dp.include_router(setup_routers(_sessionmaker)) 
    # If call_router is separate and needed:
    # from bot.callback import call_router
    # dp.include_router(call_router())

    try:
        logger.info("Starting polling...")
        await dp.start_polling(local_bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("Polling finished or interrupted. Closing bot session.")
        await local_bot.session.close()

async def main_webhook():
    session = AiohttpSession()
    local_bot = Bot(token=TOKEN, session=session) # Use local_bot
    storage = MemoryStorage()
    
    main_dispatcher = Dispatcher(storage=storage)
    main_dispatcher.workflow_data["sessionmaker"] = _sessionmaker
    main_dispatcher.startup.register(on_startup_webhook)
    main_dispatcher.shutdown.register(on_shutdown_webhook)

    db_middleware = DbSessionMiddleware(_sessionmaker)
    onboarding_middleware = OnboardingMiddleware()

    main_dispatcher.message.middleware(db_middleware)
    main_dispatcher.message.middleware(onboarding_middleware)

    main_dispatcher.business_message.middleware(db_middleware)
    main_dispatcher.business_message.middleware(onboarding_middleware)

    main_dispatcher.deleted_business_messages.middleware(db_middleware)
    main_dispatcher.deleted_business_messages.middleware(onboarding_middleware)
    main_dispatcher.edited_business_message.middleware(db_middleware)
    main_dispatcher.edited_business_message.middleware(onboarding_middleware)
    main_dispatcher.callback_query.middleware(db_middleware)
    main_dispatcher.callback_query.middleware(onboarding_middleware)
    main_dispatcher.include_router(setup_routers(_sessionmaker))

    app = web.Application()
    # Pass local_bot to the handlers that need it, or rely on DI if setup_application handles it.
    # For SimpleRequestHandler, bot instance is passed directly.

    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    # The setup_application might handle passing bot to startup/shutdown if registered via app.on_startup etc.
    # Let's ensure on_startup_webhook and on_shutdown_webhook are called with the bot instance.
    # One way is to use functools.partial or lambdas if setup_application doesn't inject bot from SimpleRequestHandler context.
    # However, SimpleRequestHandler takes the bot, and dispatcher takes the bot. Startup/shutdown registered on dispatcher should get it.

    # Correct way for webhook startup/shutdown with aiogram's setup_application or SimpleRequestHandler
    # is typically to register them on the dispatcher, and the dispatcher is given the bot.
    # The on_startup_webhook and on_shutdown_webhook are already registered on main_dispatcher.
    # When SimpleRequestHandler calls main_dispatcher.feed_update(bot, update), the bot context is set.

    SimpleRequestHandler(dispatcher=main_dispatcher, bot=local_bot).register(app, path=MAIN_BOT_PATH)
    
    # If using setup_application for the main dispatcher's lifecycle with the app:
    # setup_application(app, main_dispatcher, bot=local_bot) # This would call dispatcher's startup/shutdown

    logger.info("Starting web server on %s:%s", WEB_SERVER_HOST, WEB_SERVER_PORT)
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)
    # Ensure local_bot.session.close() is called on shutdown for webhooks too.
    # This is often handled by app.on_cleanup or a similar mechanism for aiohttp.
    # For simplicity, we'll rely on on_shutdown_webhook for now.


if __name__ == "__main__":
    args, remaining_argv = parse_cli_args()
    sys.argv = [sys.argv[0], *remaining_argv]

    configure_logging(language=args.log_language, level=args.log_level or logging.DEBUG)

    if RUN_VIA_POLLING:
        logger.info("Attempting to run in POLLING mode.")
        asyncio.run(main_polling())
    else:
        logger.info("Attempting to run in WEBHOOK mode.")
        if not BASE_URL or BASE_URL == "https://example.com":
            logger.error("BASE_URL is not configured correctly for webhook mode. Please set it in .env. Exiting.")
            sys.exit(1)
        if not MAIN_BOT_PATH:
            logger.error("MAIN_BOT_PATH is not configured. Please set it in .env. Exiting.")
            sys.exit(1)
        asyncio.run(main_webhook())
