"""Inline keyboards for the bot."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Начать диагностику", callback_data="start_diagnostic")],
    ])


ROLES = [
    "CEO / Founder",
    "C-level",
    "Руководитель функции",
    "Data / AI / IT",
    "HR / Operations",
    "Консультант",
    "Другое",
]


def role_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=role, callback_data=f"role:{role}")]
        for role in ROLES
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def question_keyboard(options: list[dict], question_order: int) -> InlineKeyboardMarkup:
    """Build answer buttons for a question.

    options: list of {"id", "label_short", "score"}
    """
    buttons = [
        [InlineKeyboardButton(
            text=opt["label_short"],
            callback_data=f"ans:{question_order}:{opt['id']}:{opt['score']}",
        )]
        for opt in options
    ]
    # "Не знаю" button
    buttons.append([
        InlineKeyboardButton(
            text="🤷 Не знаю",
            callback_data=f"ans:{question_order}:0:0",
        )
    ])
    # Navigation
    nav_row = []
    if question_order > 1:
        nav_row.append(InlineKeyboardButton(text="◀ Назад", callback_data="nav:back"))
    nav_row.append(InlineKeyboardButton(text="⏹ Прервать", callback_data="nav:stop"))
    buttons.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def category_complete_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶ Продолжить", callback_data="nav:continue")],
        [InlineKeyboardButton(text="⏹ Прервать", callback_data="nav:stop")],
    ])


def confirm_stop_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, выйти", callback_data="confirm:stop_yes")],
        [InlineKeyboardButton(text="Продолжить", callback_data="confirm:stop_no")],
    ])


def confirm_restart_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, начать заново", callback_data="confirm:restart_yes")],
        [InlineKeyboardButton(text="Отмена", callback_data="confirm:restart_no")],
    ])


def results_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Получить PDF", callback_data="result:pdf")],
        [InlineKeyboardButton(text="📋 Детали по категориям", callback_data="result:details")],
        [InlineKeyboardButton(text="📞 Оставить контакты", callback_data="result:contact")],
        [InlineKeyboardButton(text="💬 Запросить консультацию", callback_data="result:consult")],
        [InlineKeyboardButton(text="🔄 Пройти заново", callback_data="nav:restart")],
    ])


def contact_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅ Назад к результатам", callback_data="result:back")],
    ])
