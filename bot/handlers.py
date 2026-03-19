"""
Telegram bot handlers for AI Maturity Index assessment.
Uses aiogram 3.x with inline keyboards.
Edits messages in-place to keep chat clean.
"""

import csv
import io
import json
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot import database as db
from bot import texts
from bot.config import settings
from bot.questions import CATEGORIES, CATEGORY_BY_CODE, QUESTIONS
from bot.scoring import calculate_results

logger = logging.getLogger(__name__)
router = Router()


# ── Helpers ──


def _progress_bar(current: int, total: int = 35, width: int = 14) -> str:
    filled = round(current / total * width)
    bar = "▓" * filled + "░" * (width - filled)
    return f"[{bar}] {current}/{total}"


def _question_keyboard(question_index: int) -> InlineKeyboardMarkup:
    """Build inline keyboard for a question: answer buttons 1-5, back, pause."""
    q = QUESTIONS[question_index]
    buttons = []
    for opt in q.options:
        buttons.append([
            InlineKeyboardButton(
                text=f"{opt.score}",
                callback_data=f"ans:{question_index}:{opt.score}",
            )
        ])
    nav_row = []
    if question_index > 0:
        nav_row.append(
            InlineKeyboardButton(text="◀ Назад", callback_data=f"back:{question_index}")
        )
    nav_row.append(
        InlineKeyboardButton(text="Прервать", callback_data="pause")
    )
    buttons.append(nav_row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _question_text(question_index: int) -> str:
    """Format question message with category, progress, options."""
    q = QUESTIONS[question_index]
    cat = CATEGORY_BY_CODE[q.category_code]
    cat_questions = [qq for qq in QUESTIONS if qq.category_code == q.category_code]
    q_in_cat = next(i for i, qq in enumerate(cat_questions) if qq.id == q.id) + 1

    lines = [
        f"<b>{cat.name}</b>  •  Вопрос {q_in_cat} из {len(cat_questions)}",
        _progress_bar(question_index + 1),
        "",
        f"<b>{q.text}</b>",
        "",
    ]
    for opt in q.options:
        lines.append(f"{opt.score}. {opt.text}")

    return "\n".join(lines)


def _result_text(result: dict) -> str:
    """Format the final result message."""
    lines = [texts.RESULT_HEADER]

    # Overall
    lines.append(
        f"<b>Общий индекс ИИ-зрелости: {result['total_percent']}%</b>"
    )
    lines.append(f"Уровень: <b>{result['maturity_level']}</b>")
    lines.append("")

    # Categories
    lines.append("<b>Оценки по категориям:</b>")
    for cat in CATEGORIES:
        cat_data = result["categories"][cat.code]
        bar_len = round(cat_data["percent"] / 100 * 10)
        bar = "▓" * bar_len + "░" * (10 - bar_len)
        lines.append(f"  {cat.name}: {cat_data['percent']}%  [{bar}]")
    lines.append("")

    # Strong zones
    lines.append("<b>Сильные стороны:</b>")
    for zone in result["strong_zones"]:
        lines.append(f"  ✦ {zone['name']} — {zone['percent']}%")
    lines.append("")

    # Weak zones
    lines.append("<b>Зоны роста:</b>")
    for zone in result["weak_zones"]:
        lines.append(f"  ▸ {zone['name']} — {zone['percent']}%")
    lines.append("")

    # Interpretation
    lines.append(f"<i>{result['interpretation']}</i>")
    lines.append("")

    # Recommendations
    if result.get("recommendations"):
        lines.append("<b>Рекомендации:</b>")
        for rec in result["recommendations"]:
            lines.append(f"\n<b>{rec['category']}:</b>")
            lines.append(f"{rec['text']}")

    lines.append(texts.CTA_TEXT)
    return "\n".join(lines)


def _result_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оставить контакты", callback_data="cta:contact")],
            [InlineKeyboardButton(text="Пройти заново", callback_data="cta:restart")],
        ]
    )


def _welcome_keyboard(has_active: bool) -> InlineKeyboardMarkup:
    buttons = []
    if has_active:
        buttons.append([
            InlineKeyboardButton(text="Продолжить", callback_data="continue"),
        ])
        buttons.append([
            InlineKeyboardButton(text="Начать заново", callback_data="restart"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="Начать диагностику", callback_data="start_assessment"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ── /start command ──


@router.message(Command("start"))
async def cmd_start(message: Message):
    user = await db.get_or_create_user(
        telegram_user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    active = await db.get_active_assessment(user["id"])
    text = texts.WELCOME
    if active:
        text += texts.WELCOME_CONTINUE
    await message.answer(
        text,
        reply_markup=_welcome_keyboard(has_active=bool(active)),
        parse_mode="HTML",
    )


# ── Start / Continue / Restart assessment ──


@router.callback_query(F.data == "start_assessment")
async def cb_start_assessment(callback: CallbackQuery):
    user = await db.get_or_create_user(
        telegram_user_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    assessment = await db.create_assessment(user["id"])
    await _show_question(callback, 0)


@router.callback_query(F.data == "continue")
async def cb_continue(callback: CallbackQuery):
    user = await db.get_or_create_user(
        telegram_user_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    active = await db.get_active_assessment(user["id"])
    if not active:
        await callback.answer("Активная сессия не найдена. Начните заново.")
        return
    await _show_question(callback, active["current_question_index"])


@router.callback_query(F.data == "restart")
async def cb_restart(callback: CallbackQuery):
    user = await db.get_or_create_user(
        telegram_user_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    assessment = await db.create_assessment(user["id"])
    await _show_question(callback, 0)


# ── Answer handling ──


@router.callback_query(F.data.startswith("ans:"))
async def cb_answer(callback: CallbackQuery):
    parts = callback.data.split(":")
    question_index = int(parts[1])
    score = int(parts[2])

    user = await db.get_or_create_user(
        telegram_user_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    active = await db.get_active_assessment(user["id"])
    if not active:
        await callback.answer(texts.SESSION_EXPIRED)
        return

    question = QUESTIONS[question_index]
    await db.save_answer(active["id"], question.id, score)

    next_index = question_index + 1
    await db.update_assessment_question_index(active["id"], next_index)

    if next_index >= len(QUESTIONS):
        # Assessment complete — calculate results
        answers = await db.get_answers_for_assessment(active["id"])
        result = calculate_results(answers)
        await db.complete_assessment(
            active["id"],
            result["total_percent"],
            result["maturity_level"],
            result,
        )
        await callback.message.edit_text(
            _result_text(result),
            reply_markup=_result_keyboard(),
            parse_mode="HTML",
        )
    else:
        await _show_question(callback, next_index)

    await callback.answer()


# ── Back button ──


@router.callback_query(F.data.startswith("back:"))
async def cb_back(callback: CallbackQuery):
    question_index = int(callback.data.split(":")[1])
    prev_index = question_index - 1
    if prev_index < 0:
        await callback.answer()
        return

    user = await db.get_or_create_user(
        telegram_user_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    active = await db.get_active_assessment(user["id"])
    if active:
        # Delete the answer for the current question so user can re-answer
        await db.delete_answers_from(active["id"], QUESTIONS[question_index].id)
        await db.update_assessment_question_index(active["id"], prev_index)

    await _show_question(callback, prev_index)
    await callback.answer()


# ── Pause ──


@router.callback_query(F.data == "pause")
async def cb_pause(callback: CallbackQuery):
    await callback.message.edit_text(texts.PAUSED, parse_mode="HTML")
    await callback.answer()


# ── CTA handlers ──


@router.callback_query(F.data == "cta:contact")
async def cb_contact(callback: CallbackQuery):
    await callback.message.answer(texts.CONTACT_REQUEST, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "cta:restart")
async def cb_cta_restart(callback: CallbackQuery):
    user = await db.get_or_create_user(
        telegram_user_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    assessment = await db.create_assessment(user["id"])
    await _show_question(callback, 0)
    await callback.answer()


# ── Contact info collection (free-form message after CTA) ──


@router.message(F.text.regexp(r".+,.+,.+,.+"))
async def handle_contact_info(message: Message):
    """Parse contact info in format: Name, Company, Position, Email"""
    parts = [p.strip() for p in message.text.split(",", 3)]
    if len(parts) >= 4:
        await db.update_user_contact_info(
            telegram_user_id=message.from_user.id,
            company_name=parts[1],
            position=parts[2],
            email=parts[3],
        )
        await message.answer(texts.CONTACT_SAVED, parse_mode="HTML")


# ── Admin commands ──


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not _is_admin(message.from_user.id):
        return
    stats = await db.get_assessment_stats()
    text = (
        "<b>Статистика</b>\n\n"
        f"Всего начато: {stats['total_starts']}\n"
        f"Завершено: {stats['total_completed']}\n"
        f"В процессе: {stats['total_in_progress']}\n"
        f"Брошено: {stats['total_abandoned']}\n"
        f"Средний балл: {stats['avg_score']}%"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("export"))
async def cmd_export(message: Message):
    if not _is_admin(message.from_user.id):
        return
    assessments = await db.get_all_completed_assessments()
    if not assessments:
        await message.answer("Нет завершённых диагностик.")
        return

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "assessment_id", "telegram_user_id", "username", "first_name",
        "last_name", "company", "position", "industry",
        "started_at", "completed_at", "total_score_percent", "maturity_level",
    ] + [c.name for c in CATEGORIES])

    for a in assessments:
        result = json.loads(a["result_json"]) if a["result_json"] else {}
        cat_scores = []
        for cat in CATEGORIES:
            cat_data = result.get("categories", {}).get(cat.code, {})
            cat_scores.append(cat_data.get("percent", ""))
        writer.writerow([
            a["assessment_id"], a["telegram_user_id"], a["username"],
            a["first_name"], a["last_name"], a["company_name"],
            a["position"], a["industry"],
            a["started_at"], a["completed_at"],
            a["total_score_percent"], a["maturity_level"],
        ] + cat_scores)

    output.seek(0)
    file = BufferedInputFile(
        output.getvalue().encode("utf-8-sig"),
        filename=f"ai_maturity_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    )
    await message.answer_document(file, caption="Выгрузка завершённых диагностик")


# ── Helper to show question ──


async def _show_question(callback: CallbackQuery, question_index: int):
    """Edit the current message to show a question."""
    text = _question_text(question_index)
    keyboard = _question_keyboard(question_index)
    try:
        await callback.message.edit_text(
            text, reply_markup=keyboard, parse_mode="HTML"
        )
    except Exception:
        # If edit fails (e.g., message too old), send new message
        await callback.message.answer(
            text, reply_markup=keyboard, parse_mode="HTML"
        )
