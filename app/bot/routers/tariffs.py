from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app.db import admins as admins_repo
from app.db import payments as payments_repo
from app.db import pricing as pricing_repo
from app.db import settings as settings_repo
from app.payments.poller import poll_payment
from app.payments.yookassa_provider import yookassa_provider
from app.services import subscription_service, texts
from app.services.keyboards import BTN_BUY, how_to_use_button, pay_link, tariffs
from app.services.ui import clear_ephemeral, send_ephemeral, send_persistent
from app.vpn.manager import NoCapacityError

logger = logging.getLogger(__name__)
router = Router(name="tariffs")


async def _show_tariffs(bot: Bot, chat_id: int) -> None:
    tariffs_list = pricing_repo.get_all()
    trial_enabled = settings_repo.get_bool("trial_enabled", True)
    await send_ephemeral(bot, chat_id, texts.tariffs_intro(), reply_markup=tariffs(tariffs_list, trial_enabled))


@router.message(F.text == BTN_BUY)
async def btn_buy(message: Message, bot: Bot):
    await _show_tariffs(bot, message.chat.id)


@router.callback_query(F.data == "buy_menu")
async def cb_buy_menu(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    await _show_tariffs(bot, callback.message.chat.id)


@router.callback_query(F.data.startswith("tariff:"))
async def cb_tariff_selected(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    tariff_key = callback.data.split(":", 1)[1]
    tariff = pricing_repo.get(tariff_key)
    if not tariff:
        return

    telegram_id = callback.from_user.id
    chat_id = callback.message.chat.id

    if not subscription_service.has_capacity_for(telegram_id):
        await send_ephemeral(bot, chat_id, texts.no_capacity())
        return

    try:
        link = yookassa_provider.create_payment(
            amount=tariff["price"],
            description=f"Подписка VPN — {tariff['label']}",
            metadata={"telegram_id": telegram_id, "tariff_key": tariff_key},
        )
    except Exception as e:
        logger.error("Failed to create payment for user %s: %s", telegram_id, e)
        await send_ephemeral(bot, chat_id, texts.payment_creation_failed())
        return

    payments_repo.create(
        payment_id=link.payment_id,
        telegram_id=telegram_id,
        chat_id=chat_id,
        tariff_key=tariff_key,
        amount=tariff["price"],
    )

    await send_ephemeral(
        bot,
        chat_id,
        texts.payment_link_message(tariff["label"], tariff["price"]),
        reply_markup=pay_link(link.url),
    )

    asyncio.create_task(track_payment(bot, link.payment_id, telegram_id, chat_id, tariff_key))


async def track_payment(bot: Bot, payment_id: str, telegram_id: int, chat_id: int, tariff_key: str) -> None:
    async def on_succeeded() -> None:
        await clear_ephemeral(bot, chat_id)
        try:
            result = subscription_service.activate_purchase(telegram_id, tariff_key)
        except NoCapacityError:
            await send_persistent(bot, chat_id, texts.no_capacity())
            await _alert_admins_no_capacity(bot, payment_id, telegram_id, tariff_key)
            return
        except Exception as e:
            logger.exception("Failed to activate purchase for user %s: %s", telegram_id, e)
            await send_persistent(bot, chat_id, texts.payment_creation_failed())
            return

        expires_str = result.new_expires_at.strftime("%d.%m.%Y")
        await send_persistent(bot, chat_id, texts.payment_succeeded(expires_str, result.extended))
        await bot.send_document(
            chat_id,
            BufferedInputFile(result.acquired.conf_text.encode(), filename="vpn.conf"),
            caption=texts.key_file_caption(expires_str),
            parse_mode="HTML",
        )
        await bot.send_message(chat_id, texts.use_key_prompt(), reply_markup=how_to_use_button())

    async def on_terminal_failure(reason: str) -> None:
        await clear_ephemeral(bot, chat_id)
        if reason == "canceled":
            await send_ephemeral(bot, chat_id, texts.payment_canceled())
        else:
            await send_ephemeral(bot, chat_id, texts.payment_timed_out())

    await poll_payment(
        yookassa_provider,
        payment_id,
        on_succeeded=on_succeeded,
        on_terminal_failure=on_terminal_failure,
    )


async def _alert_admins_no_capacity(bot: Bot, payment_id: str, telegram_id: int, tariff_key: str) -> None:
    """Payment succeeded but no VPN capacity was available at fulfillment — a human
    needs to manually refund via the YooKassa dashboard or free up a slot."""
    payment = payments_repo.get(payment_id)
    amount = payment["amount"] if payment else "?"
    text = (
        "⚠️ <b>Оплата прошла, но не хватило места для подписки!</b>\n\n"
        f"👤 Пользователь: <code>{telegram_id}</code>\n"
        f"💳 Платёж: <code>{payment_id}</code>\n"
        f"📦 Тариф: {tariff_key}\n"
        f"💰 Сумма: {amount} ₽\n\n"
        "Нужно вручную оформить возврат или освободить слот и повторно активировать подписку."
    )
    for admin in admins_repo.list_admins():
        try:
            await bot.send_message(admin["telegram_id"], text, parse_mode="HTML")
        except Exception as e:
            logger.warning("Failed to alert admin %s about capacity failure: %s", admin["telegram_id"], e)
