from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_for_lookup_id = State()
    waiting_for_add_admin_id = State()
