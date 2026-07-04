from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.config import BASE_DIR, settings
from app.db import admins as admins_repo
from app.services import subscription_service, texts
from app.services.keyboards import channel_gate, main_menu

logger = logging.getLogger(__name__)
router = Router(name="start")


async def _is_subscribed_to_channel(bot: Bot, user_id: int) -> bool:
    if not settings.require_channel_subscription or not settings.news_channel:
        return True
    try:
        member = await bot.get_chat_member(settings.news_channel, user_id)
        return member.status not in ("left", "kicked")
    except Exception as e:
        logger.warning("Could not check channel subscription for %s: %s", user_id, e)
        return True  # fail open — never lock users out because of a transient API error


async def _send_welcome(bot: Bot, chat_id: int, user_id: int, name: str) -> None:
    is_admin = admins_repo.is_admin(user_id)
    view = subscription_service.get_view(user_id)
    if view["days_left"] > 0:
        text = texts.welcome_back(name, view["days_left"], view["is_trial"])
    else:
        text = texts.welcome_new(name)

    image_path = BASE_DIR / "assets" / "main2.png"
    markup = main_menu(is_admin=is_admin)
    try:
        if image_path.exists():
            await bot.send_photo(chat_id, FSInputFile(image_path), caption=text, parse_mode="HTML", reply_markup=markup)
            return
    except Exception as e:
        logger.warning("Failed to send welcome photo: %s", e)
    await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)


@router.message(Command("start"))
async def cmd_start(message: Message, bot: Bot):
    user = message.from_user
    name = (user.first_name or "").strip() or "друг"

    if not await _is_subscribed_to_channel(bot, user.id):
        await message.answer(
            texts.channel_gate(settings.news_channel),
            parse_mode="HTML",
            reply_markup=channel_gate(settings.news_channel),
        )
        return

    await _send_welcome(bot, message.chat.id, user.id, name)


@router.callback_query(F.data == "check_channel_sub")
async def cb_check_channel_sub(callback: CallbackQuery, bot: Bot):
    if not await _is_subscribed_to_channel(bot, callback.from_user.id):
        await callback.answer(texts.not_subscribed_yet(), show_alert=True)
        return
    await callback.answer("✅ Отлично!")
    try:
        await callback.message.delete()
    except Exception:
        pass
    name = (callback.from_user.first_name or "").strip() or "друг"
    await _send_welcome(bot, callback.message.chat.id, callback.from_user.id, name)
