from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.middlewares import UserSyncMiddleware
from app.bot.routers import instructions, misc, my_subscription, start, tariffs, trial
from app.bot.routers.admin import admins as admin_admins
from app.bot.routers.admin import panel as admin_panel
from app.bot.routers.admin import pricing as admin_pricing
from app.bot.routers.admin import servers as admin_servers
from app.bot.routers.admin import users as admin_users
from app.bot.routers.admin import changetime as admin_changetime
from app.config import settings


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.outer_middleware(UserSyncMiddleware())
    dp.callback_query.outer_middleware(UserSyncMiddleware())

    # Admin routers first so FSM states / admin-only commands take priority.
    dp.include_router(admin_panel.router)
    dp.include_router(admin_pricing.router)
    dp.include_router(admin_admins.router)
    dp.include_router(admin_users.router)
    dp.include_router(admin_changetime.router)
    dp.include_router(admin_servers.router)

    dp.include_router(start.router)
    dp.include_router(tariffs.router)
    dp.include_router(trial.router)
    dp.include_router(my_subscription.router)
    dp.include_router(instructions.router)
    dp.include_router(misc.router)

    return dp


def build_bot() -> Bot:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set — copy .env.example to .env and fill it in.")
    return Bot(token=settings.bot_token)
