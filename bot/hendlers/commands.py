import re
from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from bot.utils.creat import command_add_bot
from bot.utils.analytics import record_command_usage
from bot.localization import get_text


def commands_router() -> Router:
    commands = Router()

    # Helper function to validate the bot token format
    async def is_bot_token(token: str) -> bool:
        # Basic validation - check if token matches expected format
        return bool(re.match(r'^\d+:[\w-]+$', token))

    @commands.message(Command("add_bot"))
    async def add_bot_command(
        message: Message,
        command: CommandObject,
        bot: Bot,
        session: AsyncSession,
        language: str,
    ) -> None:
        """Handle the /add_bot command with a token argument"""
        await record_command_usage(session, "add_bot")
        if not command.args:
            await message.answer(get_text("add_bot_missing_token", language))
            return
        
        token = command.args
        
        # Validate the token format
        if not await is_bot_token(token):
            await message.answer(get_text("add_bot_invalid_token", language))
            return
        
        # Call the add_bot function with the extracted token and session
        await command_add_bot(
            message=message,
            bot=bot,
            token=token,
            session=session,
            language=language,
        )

    return commands
