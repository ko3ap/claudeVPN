"""Keeps the chat clean: ephemeral messages replace each other automatically,
while persistent messages (payment confirmations, expiry/reminder notices)
are sent normally and never auto-deleted.
"""
from __future__ import annotations

import logging
from typing import Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, Message

from app.db import ephemeral as ephemeral_repo

logger = logging.getLogger(__name__)


async def send_ephemeral(
    bot: Bot,
    chat_id: int,
    text: str,
    *,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "HTML",
) -> Message:
    """Send a disposable message, deleting the chat's previous ephemeral message first."""
    await clear_ephemeral(bot, chat_id)
    message = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    ephemeral_repo.set(chat_id, message.message_id)
    return message


async def clear_ephemeral(bot: Bot, chat_id: int) -> None:
    message_id = ephemeral_repo.get(chat_id)
    if not message_id:
        return
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception as e:
        logger.debug("Could not delete ephemeral message %s in chat %s: %s", message_id, chat_id, e)
    ephemeral_repo.clear(chat_id)


async def send_persistent(
    bot: Bot,
    chat_id: int,
    text: str,
    *,
    reply_markup=None,
    parse_mode: str = "HTML",
) -> Message:
    """Send an important message that stays in chat history — never auto-deleted."""
    return await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
