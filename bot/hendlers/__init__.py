from aiogram import Router
from sqlalchemy.ext.asyncio import async_sessionmaker

# Import routers
from .client import start, subscription
from .buisness import spy, check
from .commands import commands_router
from .admin import admin_router
from .token_input_handler import get_token_router

def setup_routers(sessionmaker: async_sessionmaker) -> Router:
    """Configure all routers."""
    router = Router()
    
    # Include our routers
    router.include_router(start.start_router())
    router.include_router(subscription.subscription_router(sessionmaker))
    router.include_router(admin_router())
    router.include_router(spy.spy_router())
    router.include_router(check.check_router())
    router.include_router(commands_router())
    router.include_router(get_token_router())
    
    return router
