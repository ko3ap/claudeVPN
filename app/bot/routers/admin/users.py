from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.routers.admin.guards import ensure_admin
from app.bot.states import AdminStates
from app.db import subscriptions as subs_repo
from app.db import users as users_repo
from app.db import vpn_clients as clients_repo
from app.services import subscription_service
from app.services.keyboards import admin_cancel

router = Router(name="admin_users")


@router.message(Command("users"))
async def cmd_users(message: Message):
    if not await ensure_admin(message):
        return
    active = subs_repo.get_active_users()
    if not active:
        await message.answer("Нет пользователей с активной подпиской.")
        return

    lines = ["👥 <b>Активные пользователи</b>\n"]
    for sub in active:
        uname = f"@{sub['username']}" if sub.get("username") else str(sub["telegram_id"])
        days = subscription_service.days_left(sub["expires_at"])
        kind = "пробный" if sub["status"] == "trial" else "платный"
        lines.append(f"• {uname} ({sub['telegram_id']}) — {days} дн. [{kind}]")
    await message.answer("\n".join(lines), parse_mode="HTML")


def _format_profile(telegram_id: int) -> str:
    user = users_repo.get_user(telegram_id)
    view = subscription_service.get_view(telegram_id)
    client = clients_repo.get_by_user(telegram_id)

    lines = [f"🔍 <b>Пользователь {telegram_id}</b>\n"]
    if user:
        uname = f"@{user['username']}" if user.get("username") else "—"
        lines.append(f"Username: {uname}")
    else:
        lines.append("⚠️ Пользователь не найден в базе.")

    lines.append(f"Статус подписки: <b>{view['status']}</b>")
    lines.append(f"Осталось дней: <b>{view['days_left']}</b>")
    lines.append(f"Пробный период использован: {'да' if view['trial_used'] else 'нет'}")

    if view["expires_at"]:
        exp = datetime.fromisoformat(view["expires_at"]).strftime("%d.%m.%Y %H:%M")
        lines.append(f"Истекает: {exp}")

    if client:
        lines.append(
            f"\n🔑 VPN-клиент: статус <b>{client['status']}</b>, адрес: {client['address']}"
        )
    else:
        lines.append("\n🔑 VPN-клиент не выдавался.")

    return "\n".join(lines)


@router.callback_query(F.data == "admin:find")
async def cb_admin_find_start(callback: CallbackQuery, state: FSMContext):
    if not await ensure_admin(callback):
        return
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_lookup_id)
    await callback.message.edit_text(
        "Пришли Telegram ID (chat id) пользователя для поиска.", reply_markup=admin_cancel()
    )


@router.message(AdminStates.waiting_for_lookup_id)
async def msg_admin_find_id(message: Message, state: FSMContext):
    if not await ensure_admin(message):
        return
    try:
        target_id = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("ID должен быть числом. Попробуй ещё раз или нажми «Отмена».")
        return

    await state.clear()
    await message.answer(_format_profile(target_id), parse_mode="HTML")
