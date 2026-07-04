"""Admin pricing panel — tariff prices are adjusted with +/- buttons instead of
free-text input. A price decrease triggers a discount broadcast to all users;
an increase never does.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from app.bot.routers.admin.guards import ensure_admin
from app.db import pricing as pricing_repo
from app.db import users as users_repo
from app.services.keyboards import admin_pricing

logger = logging.getLogger(__name__)
router = Router(name="admin_pricing")


def _pricing_text() -> str:
    return "💰 <b>Тарифы</b>\n\nНажимай +/- чтобы изменить цену. При снижении цены всем пользователям уйдёт уведомление о скидке."


@router.callback_query(F.data == "admin:pricing")
async def cb_admin_pricing(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    await callback.answer()
    await callback.message.edit_text(
        _pricing_text(), parse_mode="HTML", reply_markup=admin_pricing(pricing_repo.get_all())
    )


@router.callback_query(F.data.startswith("admin:price:"))
async def cb_admin_price_change(callback: CallbackQuery, bot: Bot):
    if not await ensure_admin(callback):
        return

    _, _, tariff_key, delta_str = callback.data.split(":")
    delta = int(delta_str)

    tariff = pricing_repo.get(tariff_key)
    if not tariff:
        await callback.answer("Тариф не найден.", show_alert=True)
        return

    new_price = max(1, tariff["price"] + delta)
    old_price = pricing_repo.update_price(tariff_key, new_price)
    await callback.answer(f"{tariff['label']}: {new_price} ₽")

    await callback.message.edit_text(
        _pricing_text(), parse_mode="HTML", reply_markup=admin_pricing(pricing_repo.get_all())
    )

    if old_price is not None and new_price < old_price:
        asyncio.create_task(_broadcast_discount(bot, tariff["label"], old_price, new_price))


async def _broadcast_discount(bot: Bot, label: str, old_price: int, new_price: int) -> None:
    text = (
        f"🔥 <b>Снижена цена на тариф «{label}»!</b>\n\n"
        f"Было {old_price} ₽ — стало <b>{new_price} ₽</b>.\n\n"
        "Отличный повод оформить или продлить подписку 😊"
    )
    sent, failed = 0, 0
    for user_id in users_repo.get_all_user_ids():
        try:
            await bot.send_message(user_id, text, parse_mode="HTML")
            sent += 1
        except Exception as e:
            failed += 1
            logger.debug("Broadcast failed for user %s: %s", user_id, e)
    logger.info("Discount broadcast for %s: sent=%s failed=%s", label, sent, failed)
