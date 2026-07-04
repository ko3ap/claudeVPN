"""All keyboard builders, centralized so callback_data strings are defined once."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

BTN_BUY = "🛒 Купить подписку"
BTN_MY_SUB = "👤 Моя подписка"
BTN_OTHER = "💬 Другое"
BTN_ADMIN = "⚙️ Админ"


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=BTN_BUY), KeyboardButton(text=BTN_MY_SUB)],
        [KeyboardButton(text=BTN_OTHER)],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def channel_gate(channel_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подписаться на канал", url=f"https://t.me/{channel_username.lstrip('@')}")],
            [InlineKeyboardButton(text="🔄 Проверить подписку", callback_data="check_channel_sub")],
        ]
    )


def tariffs(tariffs_list: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{t['label']} — {t['price']} ₽", callback_data=f"tariff:{t['key']}")]
        for t in tariffs_list
    ]
    rows.append([InlineKeyboardButton(text="🎁 Пробный период", callback_data="trial_offer")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pay_link(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💳 Перейти к оплате", url=url)]]
    )


def trial_activate() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Активировать пробный период", callback_data="trial_activate")]]
    )


def how_to_use_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❓ Я не знаю, как использовать ключ", callback_data="how_to_use")]]
    )


def buy_now() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🛒 Купить подписку", callback_data="buy_menu")]]
    )


def other_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="ℹ️ О сервисе", callback_data="about")],
            [InlineKeyboardButton(text="💬 Поддержка", callback_data="support")],
        ]
    )


# ─── Admin ────────────────────────────────────────────────────────────────────

def admin_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Тарифы", callback_data="admin:pricing")],
            [InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="admin:find")],
            [InlineKeyboardButton(text="👑 Администраторы", callback_data="admin:admins")],
        ]
    )


def admin_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="admin:back")]]
    )


def admin_pricing(tariffs_list: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for t in tariffs_list:
        rows.append([InlineKeyboardButton(text=f"{t['label']} — {t['price']} ₽", callback_data="noop")])
        rows.append(
            [
                InlineKeyboardButton(text="−50", callback_data=f"admin:price:{t['key']}:-50"),
                InlineKeyboardButton(text="−10", callback_data=f"admin:price:{t['key']}:-10"),
                InlineKeyboardButton(text="+10", callback_data=f"admin:price:{t['key']}:10"),
                InlineKeyboardButton(text="+50", callback_data=f"admin:price:{t['key']}:50"),
            ]
        )
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_admins_list(admins_list: list[dict], main_admin_id: int) -> InlineKeyboardMarkup:
    rows = []
    for a in admins_list:
        label = f"@{a['username']}" if a.get("username") else str(a["telegram_id"])
        if a["telegram_id"] == main_admin_id:
            rows.append([InlineKeyboardButton(text=f"👑 {label} (главный)", callback_data="noop")])
        else:
            rows.append(
                [InlineKeyboardButton(text=f"❌ Убрать {label}", callback_data=f"admin:admins:remove:{a['telegram_id']}")]
            )
    rows.append([InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin:admins:add")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✖️ Отмена", callback_data="admin:back")]]
    )
