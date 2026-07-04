from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.types import BufferedInputFile, CallbackQuery

from app.config import settings
from app.services import subscription_service, texts
from app.services.keyboards import how_to_use_button, trial_activate
from app.services.ui import clear_ephemeral, send_ephemeral, send_persistent
from app.vpn.manager import NoCapacityError

logger = logging.getLogger(__name__)
router = Router(name="trial")


@router.callback_query(F.data == "trial_offer")
async def cb_trial_offer(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    view = subscription_service.get_view(callback.from_user.id)
    if view["trial_used"]:
        await send_ephemeral(bot, callback.message.chat.id, texts.trial_already_used())
        return
    if view["status"] == "active":
        await send_ephemeral(bot, callback.message.chat.id, texts.already_subscribed())
        return

    await send_ephemeral(
        bot,
        callback.message.chat.id,
        texts.trial_offer(settings.trial_days),
        reply_markup=trial_activate(),
    )


@router.callback_query(F.data == "trial_activate")
async def cb_trial_activate(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    telegram_id = callback.from_user.id
    chat_id = callback.message.chat.id

    try:
        result = subscription_service.activate_trial(telegram_id)
    except subscription_service.TrialAlreadyUsedError:
        await send_ephemeral(bot, chat_id, texts.trial_already_used())
        return
    except subscription_service.AlreadySubscribedError:
        await send_ephemeral(bot, chat_id, texts.already_subscribed())
        return
    except NoCapacityError:
        await send_ephemeral(bot, chat_id, texts.no_capacity())
        return

    await clear_ephemeral(bot, chat_id)
    await send_persistent(bot, chat_id, texts.trial_activated(settings.trial_days))
    await bot.send_document(
        chat_id,
        BufferedInputFile(result.acquired.conf_text.encode(), filename="vpn.conf"),
        caption=texts.key_file_caption(result.new_expires_at.strftime("%d.%m.%Y")),
        parse_mode="HTML",
    )
    await bot.send_message(chat_id, texts.use_key_prompt(), reply_markup=how_to_use_button())
