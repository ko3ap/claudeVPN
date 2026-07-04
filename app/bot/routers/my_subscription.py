from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import Message

from app.services import subscription_service, texts
from app.services.keyboards import BTN_MY_SUB, buy_now

router = Router(name="my_subscription")


@router.message(F.text == BTN_MY_SUB)
async def btn_my_subscription(message: Message, bot: Bot):
    view = subscription_service.get_view(message.from_user.id)

    if view["days_left"] <= 0:
        # Telegram only supports true popups on callback queries, not plain
        # keyboard-button presses — this message + button is the closest
        # equivalent: an unmissable notice with a one-tap path to buy.
        await message.answer(
            texts.no_active_subscription_message(),
            parse_mode="HTML",
            reply_markup=buy_now(),
        )
        return

    expires_str = ""
    if view["expires_at"]:
        from datetime import datetime

        expires_str = datetime.fromisoformat(view["expires_at"]).strftime("%d.%m.%Y")

    await message.answer(
        texts.my_subscription_active(view["days_left"], view["is_trial"], expires_str),
        parse_mode="HTML",
    )
