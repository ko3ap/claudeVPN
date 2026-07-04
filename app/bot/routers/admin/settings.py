"""Admin-controlled runtime settings: trial on/off and the VPN key pool
(enable/disable + buffer size). Stored in app_settings, editable without a
bot restart, unlike app.config.settings.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.routers.admin.guards import ensure_admin
from app.db import settings as settings_repo
from app.services.keyboards import admin_settings

router = Router(name="admin_settings")


def _current_settings() -> dict:
    return {
        "trial_enabled": settings_repo.get_bool("trial_enabled", True),
        "vpn_pool_enabled": settings_repo.get_bool("vpn_pool_enabled", True),
        "vpn_pool_buffer_size": settings_repo.get_int("vpn_pool_buffer_size", 5),
    }


def _settings_text() -> str:
    return (
        "⚙️ <b>Настройки</b>\n\n"
        "🎁 Пробный период — доступность бесплатного пробного периода для новых пользователей.\n"
        "🔑 Автогенерация ключей — заранее создаёт запасные VPN-ключи, чтобы покупка/пробный период "
        "выдавались мгновенно, без ожидания создания ключа на сервере."
    )


@router.callback_query(F.data == "admin:settings")
async def cb_admin_settings(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    await callback.answer()
    await callback.message.edit_text(
        _settings_text(), parse_mode="HTML", reply_markup=admin_settings(_current_settings())
    )


@router.callback_query(F.data == "admin:settings:trial:toggle")
async def cb_admin_settings_trial_toggle(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    enabled = settings_repo.get_bool("trial_enabled", True)
    settings_repo.set("trial_enabled", "0" if enabled else "1")
    await callback.answer("Пробный период выключен" if enabled else "Пробный период включен")
    await callback.message.edit_text(
        _settings_text(), parse_mode="HTML", reply_markup=admin_settings(_current_settings())
    )


@router.callback_query(F.data == "admin:settings:pool:toggle")
async def cb_admin_settings_pool_toggle(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    enabled = settings_repo.get_bool("vpn_pool_enabled", True)
    settings_repo.set("vpn_pool_enabled", "0" if enabled else "1")
    await callback.answer("Автогенерация ключей выключена" if enabled else "Автогенерация ключей включена")
    await callback.message.edit_text(
        _settings_text(), parse_mode="HTML", reply_markup=admin_settings(_current_settings())
    )


@router.callback_query(F.data.startswith("admin:settings:pool:buffer:"))
async def cb_admin_settings_pool_buffer(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    delta = int(callback.data.rsplit(":", 1)[1])
    current = settings_repo.get_int("vpn_pool_buffer_size", 5)
    new_value = max(0, current + delta)
    settings_repo.set("vpn_pool_buffer_size", str(new_value))
    await callback.answer(f"Резерв ключей: {new_value}")
    await callback.message.edit_text(
        _settings_text(), parse_mode="HTML", reply_markup=admin_settings(_current_settings())
    )
