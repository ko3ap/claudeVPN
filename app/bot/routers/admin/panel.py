from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.db import servers as servers_repo
from app.db import subscriptions as subs_repo
from app.services.keyboards import BTN_ADMIN, admin_panel
from app.bot.routers.admin.guards import ensure_admin

router = Router(name="admin_panel")


def _stats_text() -> str:
    servers = servers_repo.list_servers(enabled_only=False)
    active_users = subs_repo.get_active_users()

    total_capacity = sum(s["max_clients"] for s in servers if s["enabled"])
    total_occupied = sum(servers_repo.count_occupied_slots(s["id"]) for s in servers if s["enabled"])

    lines = [
        "⚙️ <b>Панель администратора</b>\n",
        f"👥 Активных подписок: <b>{len(active_users)}</b>",
        f"🖥 Серверов включено: <b>{sum(1 for s in servers if s['enabled'])}</b> из {len(servers)}",
        f"📦 Занято слотов: <b>{total_occupied}</b> из {total_capacity}",
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
