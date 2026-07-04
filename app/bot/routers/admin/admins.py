"""Admin-role management — adding/removing admins is restricted to the main
admin (configured via MAIN_ADMIN_USERNAME), everyone else in the admins table
can use the rest of the panel.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.routers.admin.guards import ensure_admin, ensure_main_admin
from app.bot.states import AdminStates
from app.config import settings
from app.db import admins as admins_repo
from app.services.keyboards import admin_admins_list, admin_cancel

router = Router(name="admin_admins")


def _admins_text() -> str:
    return "👑 <b>Администраторы</b>"


@router.callback_query(F.data == "admin:admins")
async def cb_admin_admins(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    await callback.answer()
    await callback.message.edit_text(
        _admins_text(),
        parse_mode="HTML",
        reply_markup=admin_admins_list(admins_repo.list_admins(), settings.main_admin_id),
    )


@router.callback_query(F.data == "admin:admins:add")
async def cb_admin_add_start(callback: CallbackQuery, state: FSMContext):
    if not await ensure_main_admin(callback):
        return
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_add_admin_id)
    await callback.message.edit_text(
        "Пришли Telegram ID пользователя, которого нужно сделать администратором.",
        reply_markup=admin_cancel(),
    )


@router.message(AdminStates.waiting_for_add_admin_id)
async def msg_admin_add_id(message: Message, state: FSMContext):
    if not await ensure_main_admin(message):
        return
    try:
        new_admin_id = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("ID должен быть числом. Попробуй ещё раз или нажми «Отмена».")
        return

    admins_repo.add_admin(new_admin_id, username=None, added_by=message.from_user.id)
    await state.clear()
    await message.answer(
        f"✅ Пользователь <code>{new_admin_id}</code> назначен администратором.",
        parse_mode="HTML",
        reply_markup=admin_admins_list(admins_repo.list_admins(), settings.main_admin_id),
    )


@router.callback_query(F.data.startswith("admin:admins:remove:"))
async def cb_admin_remove(callback: CallbackQuery):
    if not await ensure_main_admin(callback):
        return
    target_id = int(callback.data.rsplit(":", 1)[1])
    if target_id == settings.main_admin_id:
        await callback.answer("Нельзя удалить главного администратора.", show_alert=True)
        return

    admins_repo.remove_admin(target_id)
    await callback.answer("Удалено.")
    await callback.message.edit_text(
        _admins_text(),
        parse_mode="HTML",
        reply_markup=admin_admins_list(admins_repo.list_admins(), settings.main_admin_id),
    )
