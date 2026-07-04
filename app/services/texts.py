"""All user-facing copy, centralized in one place.

Keeping every string here (instead of scattered across handlers) means the
tone stays consistent and future wording tweaks touch one file.
"""
from __future__ import annotations

from app.config import settings


def welcome_new(name: str) -> str:
    return (
        f"👋 Привет, <b>{name}</b>!\n\n"
        "Рад, что тебя заинтересовал мой VPN. Я делал его в первую очередь для себя — "
        "чтобы пользоваться быстрым и стабильным соединением — и теперь делюсь им с теми, "
        "кому это тоже нужно.\n\n"
        "<b>Почему стоит попробовать:</b>\n"
        "✔️ Некоммерческий проект — без перегруженных серверов и толп пользователей\n"
        "✔️ Ограниченное число подключений на сервер — стабильная скорость для всех\n"
        "✔️ Полная открытость — всегда отвечу на вопросы о том, как всё устроено\n\n"
        "Нажми <b>🛒 Купить подписку</b>, чтобы выбрать тариф, или попробуй "
        "бесплатный пробный период 👇"
    )


def welcome_back(name: str, days_left: int, is_trial: bool) -> str:
    kind = "пробный период" if is_trial else "подписка"
    return (
        f"👋 С возвращением, <b>{name}</b>!\n\n"
        f"Твой VPN активен 💪\n"
        f"📅 {kind.capitalize()}: осталось <b>{days_left} дн.</b>"
    )


def channel_gate(channel_url: str) -> str:
    return (
        "❗ Чтобы продолжить, подпишись на наш канал — там новости и важные обновления.\n\n"
        f"📢 {channel_url}\n\n"
        "После подписки нажми <b>🔄 Проверить подписку</b>."
    )


def not_subscribed_yet() -> str:
    return "Ты ещё не подписался на канал 🙁"


# ─── Tariffs / purchase ──────────────────────────────────────────────────────

def tariffs_intro() -> str:
    return (
        "💳 <b>Выбери тариф</b>\n\n"
        "Все планы дают полный доступ к VPN без ограничений по скорости.\n\n"
        "ℹ️ Если у тебя уже есть активная подписка, новые дни просто "
        "<b>добавятся</b> к оставшимся — доступ не прервётся.\n\n"
        "Также доступен бесплатный пробный период — 2 дня, чтобы оценить качество связи."
    )


def tariff_button(label: str, price: int) -> str:
    return f"{label} — {price} ₽"


def payment_link_message(label: str, price: int) -> str:
    return (
        f"💳 <b>{label} — {price} ₽</b>\n\n"
        "Нажми на кнопку ниже, чтобы оплатить. Как только оплата пройдёт, "
        "бот сам активирует подписку и пришлёт ключ — ничего подтверждать не нужно ✅"
    )


def payment_creation_failed() -> str:
    return "❌ Не удалось создать ссылку на оплату. Попробуй ещё раз чуть позже."


def payment_succeeded(new_expires_at_str: str, extended: bool) -> str:
    if extended:
        return (
            "✅ <b>Оплата прошла — дни добавлены к твоей подписке!</b>\n\n"
            f"📅 Новая дата окончания: <b>{new_expires_at_str}</b>"
        )
    return (
        "✅ <b>Оплата прошла, подписка активирована!</b>\n\n"
        f"📅 Действует до: <b>{new_expires_at_str}</b>"
    )


def payment_timed_out() -> str:
    return (
        "⌛ Мы не получили подтверждение оплаты вовремя.\n\n"
        "Если деньги списались — просто напиши в поддержку, разберёмся. "
        "Если нет — можешь попробовать оформить подписку заново."
    )


def payment_canceled() -> str:
    return "❌ Платёж отменён. Если это ошибка — попробуй оформить подписку заново."


def no_capacity() -> str:
    return (
        "😔 <b>Свободных мест сейчас нет</b>\n\n"
        f"Напиши в поддержку — @{settings.support_username} — и мы дадим знать, как только место освободится."
    )


def key_file_caption(expires_at_str: str) -> str:
    return f"🔑 <b>Твой VPN-ключ</b>\n📅 Активен до: {expires_at_str}"


def use_key_prompt() -> str:
    return "Не знаешь, как подключить ключ? Жми на кнопку ниже 👇"


# ─── Trial ───────────────────────────────────────────────────────────────────

def trial_offer(trial_days: int) -> str:
    return (
        f"🎉 <b>Пробный период — {trial_days} дня бесплатно!</b>\n\n"
        "Проверь скорость и стабильность соединения без каких-либо обязательств.\n\n"
        "⚠️ Важно: если во время пробного периода ты купишь подписку, "
        "оставшееся пробное время сгорает, а платная подписка начинается сразу "
        "и заново — так честнее считать дни, за которые ты платишь.\n\n"
        "Взять пробный период можно только один раз."
    )


def trial_already_used() -> str:
    return "🙁 Пробный период уже был использован — доступен только один раз."


def already_subscribed() -> str:
    return "У тебя уже есть активная подписка — пробный период сейчас не нужен 😉"


def trial_disabled() -> str:
    return (
        "🙁 <b>Пробный период временно недоступен</b>\n\n"
        f"Если есть вопросы — напиши в поддержку: @{settings.support_username}"
    )


def trial_activated(trial_days: int) -> str:
    return f"✅ <b>Пробный период активирован на {trial_days} дня!</b>\n\nЛови ключ 👇"


def trial_expiring_soon(hours_left: int) -> str:
    return (
        f"⏰ <b>Пробный период почти закончился!</b>\n\n"
        "Если тебе понравился VPN — самое время оформить подписку, чтобы не терять доступ. "
        f"Иначе через <b>{hours_left} ч.</b> доступ будет ограничен.\n\n"
        "Жми «🛒 Купить подписку», чтобы продолжить пользоваться без перерывов 🚀"
    )


# ─── My subscription ─────────────────────────────────────────────────────────

def my_subscription_active(days_left: int, is_trial: bool, expires_at_str: str) -> str:
    kind = "Пробный период" if is_trial else "Подписка"
    extra = "\n\n🔄 Можешь продлить в любой момент — новые дни добавятся к оставшимся 😊" if not is_trial else ""
    return (
        f"👤 <b>{kind}</b>\n\n"
        f"📅 Осталось: <b>{days_left} дн.</b>\n"
        f"📆 Действует до: {expires_at_str}"
        f"{extra}"
    )


def no_active_subscription_popup() -> str:
    return "У тебя нет активной подписки"


def no_active_subscription_message() -> str:
    return (
        "❌ <b>Активной подписки нет</b>\n\n"
        "Оформи подписку, чтобы начать пользоваться VPN — это займёт меньше минуты."
    )


# ─── Lifecycle notifications (persistent, never auto-deleted) ───────────────

def subscription_expired() -> str:
    return (
        "🔔 <b>Подписка закончилась</b>\n\n"
        "Доступ к VPN временно ограничен. Твой ключ сохранён ещё на 10 дней — "
        "если продлишь подписку в течение этого времени, всё восстановится "
        "автоматически и без изменений в настройке 👍"
    )


def expiry_reminder(days_left: int) -> str:
    if days_left == 1:
        return (
            "🔔 <b>Подписка заканчивается уже завтра!</b>\n\n"
            "Продли сейчас, чтобы не потерять доступ 🚀"
        )
    return (
        f"🔔 <b>До окончания подписки осталось {days_left} дн.</b>\n\n"
        "Не забудь продлить, чтобы пользоваться VPN без перерывов 🚀"
    )


# ─── Instructions / support / misc ──────────────────────────────────────────

def how_to_use() -> str:
    return (
        "📖 <b>Как использовать ключ</b>\n\n"
        "1️⃣ Установи приложение <b>AmneziaVPN</b> (рекомендуется) или совместимый WireGuard-клиент\n"
        "2️⃣ Открой присланный ботом файл <code>vpn.conf</code> через приложение\n"
        "3️⃣ Нажми «Подключиться» — готово 🚀\n\n"
        f"Если что-то не получается — пиши: @{settings.support_username}"
    )


def support() -> str:
    return (
        "<b>Есть вопросы?</b>\n\n"
        f"Пиши @{settings.support_username} — отвечу и помогу разобраться с настройкой 🚀"
    )


def about() -> str:
    return (
        "👋 Хочешь узнать больше о VPN?\n\n"
        "🔒 Проект делался с упором на качество и стабильность соединения.\n"
        "⚡️ На каждом сервере ограниченное число подключений — это держит скорость стабильно высокой.\n"
        "🌍 По мере роста добавляются новые сервера, так что мест становится больше.\n\n"
        f"Вопросы — в поддержку: @{settings.support_username} 😊"
    )


def other_menu_intro() -> str:
    return "Чем могу помочь? 😊"


def help_text() -> str:
    return (
        "ℹ️ <b>Как пользоваться ботом</b>\n\n"
        "🛒 Купить подписку — выбрать тариф и оплатить\n"
        "👤 Моя подписка — посмотреть статус и скачать ключ\n"
        "💬 Другое — поддержка и информация о сервисе"
    )
