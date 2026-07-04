from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.services import texts
from app.services.keyboards import BTN_OTHER, other_menu

router = Router(name="misc")


@router.message(F.text == BTN_OTHER)
async def btn_other(message: Message):
    await message.answer(texts.other_menu_intro(), reply_markup=other_menu())


@router.callback_query(F.data == "about")
async def cb_about(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(texts.about(), parse_mode="HTML")


@router.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(texts.support(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(texts.help_text(), parse_mode="HTML")


@router.message(Command("helpid"))
async def cmd_helpid(message: Message):
    """Hidden diagnostic command — not listed in any menu or /help text."""
    await message.answer(str(message.chat.id))


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()
