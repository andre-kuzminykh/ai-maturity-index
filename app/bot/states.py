from aiogram.fsm.state import State, StatesGroup


class DiagnosticStates(StatesGroup):
    welcome = State()
    role_selection = State()
    quiz = State()
    category_complete = State()
    confirm_stop = State()
    confirm_restart = State()
    results = State()
    contact_form = State()
