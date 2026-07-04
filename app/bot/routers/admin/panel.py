from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.db import subscriptions as subs_repo
from app.db import vpn_clients as clients_repo
from app.services.keyboards import BTN_ADMIN, admin_panel
from app.bot.routers.admin.guards import ensure_admin

router = Router(name="admin_panel")


def _stats_text() -> str:
    active_users = subs_repo.get_active_users()
    total_occupied = clients_repo.count_occupied_slots()

    lines = [
        "⚙️ <b>Панель администратора</b>\n",
        f"👥 Активных подписок: <b>{len(active_users)}</b>",
        f"📦 Занято слотов: <b>{total_occupied}</b> из {settings.vpn_max_clients}",
    ]
    return "\n".join(lines)


@router.message(Command("admin"))
@router.message(F.text == BTN_ADMIN)
async def cmd_admin(message: Message):
    if not await ensure_admin(message):
        return
    await message.answer(_stats_text(), parse_mode="HTML", reply_markup=admin_panel())


@router.callback_query(F.data == "admin:back")
async def cb_admin_back(callback: CallbackQuery):
    if not await ensure_admin(callback):
        return
    await callback.answer()
    await callback.message.edit_text(_stats_text(), parse_mode="HTML", reply_markup=admin_panel())
