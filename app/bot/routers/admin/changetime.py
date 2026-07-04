from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.routers.admin.guards import ensure_admin
from app.services import subscription_service
from app.vpn.manager import NoCapacityError

router = Router(name="admin_changetime")


@router.message(Command("changetime"))
async def cmd_changetime(message: Message):
    """/changetime <chat_id> <days> — add (or, with a negative number, remove) days.
    Replaces the old /addtime and /remtime commands.
    """
    if not await ensure_admin(message):
        return

    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Использование: /changetime <chat_id> <дни>\nПример: /changetime 123456789 -5")
        return

    try:
        target_id = int(parts[1])
        delta_days = int(parts[2])
    except ValueError:
        await message.answer("chat_id и дни должны быть целыми числами.")
        return

    try:
        new_expiry = subscription_service.change_time(target_id, delta_days)
    except NoCapacityError:
        await message.answer(
            f"❌ Не удалось изменить время пользователю {target_id}: нет свободных мест на серверах VPN. "
            "Добавьте сервер или освободите слот и повторите."
        )
        return

    if new_expiry is None:
        await message.answer(f"✅ Подписка пользователя {target_id} завершена.")
        try:
            await message.bot.send_message(
                target_id, "🔔 Ваша подписка была изменена администратором и на данный момент неактивна."
            )
        except Exception:
            pass
        return

    await message.answer(
        f"✅ Пользователю {target_id} изменено время подписки. Новая дата окончания: "
        f"{new_expiry.strftime('%d.%m.%Y')}"
    )
    try:
        verb = "добавлено" if delta_days > 0 else "изменено"
        await message.bot.send_message(
            target_id,
            f"🎁 Администратор {verb} время вашей подписки. Новая дата окончания: "
            f"{new_expiry.strftime('%d.%m.%Y')}",
        )
    except Exception:
        pass
