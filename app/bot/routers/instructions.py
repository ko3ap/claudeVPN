from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, FSInputFile

from app.config import BASE_DIR
from app.services import texts

logger = logging.getLogger(__name__)
router = Router(name="instructions")

VIDEO_PATH = BASE_DIR / "assets" / "tutVPN.mp4"


@router.callback_query(F.data == "how_to_use")
async def cb_how_to_use(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    caption = texts.how_to_use()
    try:
        if VIDEO_PATH.exists():
            await bot.send_video(
                callback.message.chat.id,
                FSInputFile(VIDEO_PATH),
                caption=caption,
                parse_mode="HTML",
            )
            return
    except Exception as e:
        logger.warning("Failed to send instructions video: %s", e)
    await bot.send_message(callback.message.chat.id, caption, parse_mode="HTML")
