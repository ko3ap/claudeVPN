"""Remaining ops commands: broadcast, DM, force-reset a subscription.

Server management commands were removed — the bot now talks to a single native
WireGuard interface configured via VPN_* settings in .env, not a registered
server fleet.
"""
from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.routers.admin.guards import ensure_admin
from app.db import users as users_repo
from app.services import subscription_service

logger = logging.getLogger(__name__)
router = Router(name="admin_servers")


@router.message(Command("ad"))
async def cmd_broadcast(message: Message, bot: Bot):
    if not await ensure_admin(message):
        return
    ad_text = message.text[len("/ad"):].strip()
    if not ad_text:
        await message.answer("Использование: /ad <текст объявления>")
        return

    count = 0
    for user_id in users_repo.get_all_user_ids():
        try:
            await bot.send_message(user_id, ad_text)
            count += 1
        except Exception as e:
            logger.debug("Broadcast failed for %s: %s", user_id, e)
    await message.answer(f"Объявление отправлено {count} пользователям.")


@router.message(Command("tell"))
async def cmd_tell(message: Message, bot: Bot):
    if not await ensure_admin(message):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /tell <chat_id> <текст>")
        return
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("chat_id должен быть числом.")
        return

    try:
        await bot.send_message(target_id, parts[2])
        await message.answer(f"✅ Сообщение отправлено {target_id}.")
    except Exception as e:
        await message.answer(f"Ошибка при отправке: {e}")


@router.message(Command("reset"))
async def cmd_reset(message: Message):
    """Admin utility: force-expire a user's subscription (e.g. for support/testing)."""
    if not await ensure_admin(message):
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Использование: /reset <chat_id>")
        return
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("chat_id должен быть числом.")
        return

    subscription_service.expire_subscription(target_id)
    await message.answer(f"Подписка пользователя {target_id} сброшена.")
