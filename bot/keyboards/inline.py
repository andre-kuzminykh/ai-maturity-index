"""Inline keyboards for the bot."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from data.question_bank import QUESTIONS


def start_keyboard(has_progress: bool = False) -> InlineKeyboardMarkup:
    if has_progress:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Продолжить", callback_data="continue")],
            [InlineKeyboardButton(text="🔄 Начать заново", callback_data="restart_confirm")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Начать диагностику", callback_data="start_assessment")],
    ])


def question_keyboard(question_index: int) -> InlineKeyboardMarkup:
    """Build keyboard for a question: 5 answer buttons + Don't know + Back + Abort."""
    q = QUESTIONS[question_index]
    buttons = []

    # Answer buttons — two per row
    row = []
    for i, btn_text in enumerate(q["buttons"]):
        row.append(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"ans:{question_index}:{i + 1}",
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Don't know
    buttons.append([
        InlineKeyboardButton(text="🤷 Не знаю", callback_data=f"ans:{question_index}:0"),
    ])

    # Navigation
    nav_row = []
    if question_index > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"back:{question_index}"))
    nav_row.append(InlineKeyboardButton(text="⏹ Прервать", callback_data="abort_confirm"))
    buttons.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def abort_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да, выйти", callback_data="abort_yes"),
            InlineKeyboardButton(text="Продолжить", callback_data="abort_no"),
        ],
    ])


def restart_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да, начать заново", callback_data="restart_yes"),
            InlineKeyboardButton(text="Отмена", callback_data="restart_no"),
        ],
    ])


def finish_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Пройти заново", callback_data="restart_confirm")],
    ])
