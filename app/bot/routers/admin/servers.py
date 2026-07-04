"""VPN server fleet management + remaining ops commands (broadcast, DM, reset).

Adding a server has no dedicated UI wizard (that's a rare, careful operation) —
it's a single pipe-delimited command so every field is explicit and reviewable
before hitting the database.
"""
from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.routers.admin.guards import ensure_admin
from app.db import servers as servers_repo
from app.db import users as users_repo
from app.services import subscription_service

logger = logging.getLogger(__name__)
router = Router(name="admin_servers")

ADD_SERVER_USAGE = (
    "Использование:\n"
    "<code>/addserver имя|docker_host|container|интерфейс|endpoint|публичный_ключ|подсеть|dns|макс_клиентов|приоритет</code>\n\n"
    "Пример:\n"
    "<code>/addserver DE-1|ssh://root@1.2.3.4|amnezia-awg|wg0|1.2.3.4:38962|SERVER_PUBKEY|10.8.0.0/24|1.1.1.1|40|100</code>"
)


@router.message(Command("servers"))
async def cmd_servers(message: Message):
    if not await ensure_admin(message):
        return
    servers = servers_repo.list_servers(enabled_only=False)
    if not servers:
        await message.answer("Серверы ещё не настроены. Добавь первый через /addserver.")
        return

    lines = ["🖥 <b>VPN-серверы</b>\n"]
    for s in servers:
        occupied = servers_repo.count_occupied_slots(s["id"])
        status = "🟢" if s["enabled"] else "🔴"
        lines.append(f"{status} <b>{s['name']}</b> — {occupied}/{s['max_clients']} · {s['endpoint']}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("addserver"))
async def cmd_addserver(message: Message):
    if not await ensure_admin(message):
        return

    raw = message.text.split(maxsplit=1)
    if len(raw) < 2:
        await message.answer(ADD_SERVER_USAGE, parse_mode="HTML")
        return

    fields = [f.strip() for f in raw[1].split("|")]
    if len(fields) != 10:
        await message.answer(ADD_SERVER_USAGE, parse_mode="HTML")
        return

    name, docker_host, container, iface, endpoint, pubkey, subnet, dns, max_clients, priority = fields
    try:
        server_id = servers_repo.add_server(
            name=name,
            docker_host=docker_host,
            container_name=container,
            interface_name=iface,
            endpoint=endpoint,
            server_public_key=pubkey,
            subnet_cidr=subnet,
            dns=dns,
            max_clients=int(max_clients),
            priority=int(priority),
        )
    except ValueError:
        await message.answer("макс_клиентов и приоритет должны быть числами.")
        return

    await message.answer(f"✅ Сервер «{name}» добавлен (id={server_id}).")


@router.message(Command("ad"))
async def cmd_broadcast(message: Message, bot: Bot):
    if not await ensure_admin(message):
        return
    ad_text = message.text[len("/ad"):].strip()
    if not ad_text:
        await message.answer("Использование: /ad <текст объявления>")
        return

    count = 0
    for user_id in users_repo.get_all_user_ids():
        try:
            await bot.send_message(user_id, ad_text)
            count += 1
        except Exception as e:
            logger.debug("Broadcast failed for %s: %s", user_id, e)
    await message.answer(f"Объявление отправлено {count} пользователям.")


@router.message(Command("tell"))
async def cmd_tell(message: Message, bot: Bot):
    if not await ensure_admin(message):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /tell <chat_id> <текст>")
        return
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("chat_id должен быть числом.")
        return

    try:
        await bot.send_message(target_id, parts[2])
        await message.answer(f"✅ Сообщение отправлено {target_id}.")
    except Exception as e:
        await message.answer(f"Ошибка при отправке: {e}")


@router.message(Command("reset"))
async def cmd_reset(message: Message):
    """Admin utility: force-expire a user's subscription (e.g. for support/testing)."""
    if not await ensure_admin(message):
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Использование: /reset <chat_id>")
        return
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("chat_id должен быть числом.")
        return

    subscription_service.expire_subscription(target_id)
    await message.answer(f"Подписка пользователя {target_id} сброшена.")
