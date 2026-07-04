"""Keeps the users table in sync on every incoming update, instead of every
handler calling update_username() individually (as the old Handlers.py did).
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.db import users as users_repo


class UserSyncMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None:
            users_repo.upsert_user(user.id, user.username, user.full_name)
        return await handler(event, data)
