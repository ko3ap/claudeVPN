from __future__ import annotations

from typing import Union

from aiogram.types import CallbackQuery, Message

from app.db import admins as admins_repo

Event = Union[Message, CallbackQuery]


async def ensure_admin(event: Event) -> bool:
    if admins_repo.is_admin(event.from_user.id):
        return True
    if isinstance(event, CallbackQuery):
        await event.answer("⛔ Недостаточно прав.", show_alert=True)
    else:
        await event.answer("⛔ У вас нет доступа к этой команде.")
    return False


async def ensure_main_admin(event: Event) -> bool:
    if admins_repo.is_main_admin(event.from_user.username):
        return True
    if isinstance(event, CallbackQuery):
        await event.answer("⛔ Это доступно только главному администратору.", show_alert=True)
    else:
        await event.answer("⛔ Эта команда доступна только главному администратору.")
    return False
