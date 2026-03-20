"""Main assessment handler — /start, questions, answers, results."""

import logging

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from data.question_bank import QUESTIONS
from bot.keyboards.inline import (
    start_keyboard,
    question_keyboard,
    abort_confirm_keyboard,
    restart_confirm_keyboard,
    finish_keyboard,
)
from bot.texts.messages import (
    welcome_text,
    question_text,
    abort_confirm_text,
    restart_confirm_text,
    result_text,
)
from services.scoring import calculate_results
from services.llm import generate_analysis, get_fallback_analysis

logger = logging.getLogger(__name__)
router = Router()


def _get_storage(event):
    return event.bot["storage"]


# ── /start ────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    storage = _get_storage(message)
    user_id = await storage.get_or_create_user(message.from_user)
    active = await storage.get_active_assessment(user_id)
    has_progress = active is not None and active["current_question_index"] > 0

    await message.answer(
        welcome_text(),
        reply_markup=start_keyboard(has_progress),
        parse_mode="HTML",
    )


# ── Start / Continue / Restart ────────────────────────────────────

@router.callback_query(F.data == "start_assessment")
async def on_start_assessment(callback: CallbackQuery):
    storage = _get_storage(callback)
    user_id = await storage.get_or_create_user(callback.from_user)
    assessment_id = await storage.create_assessment(user_id)
    callback.bot["current_assessment"] = callback.bot.get("current_assessment", {})
    callback.bot["current_assessment"][callback.from_user.id] = assessment_id

    await callback.message.edit_text(
        question_text(0),
        reply_markup=question_keyboard(0),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "continue")
async def on_continue(callback: CallbackQuery):
    storage = _get_storage(callback)
    user_id = await storage.get_or_create_user(callback.from_user)
    active = await storage.get_active_assessment(user_id)
    if not active:
        await callback.answer("Нет активной диагностики.")
        return

    idx = active["current_question_index"]
    callback.bot["current_assessment"] = callback.bot.get("current_assessment", {})
    callback.bot["current_assessment"][callback.from_user.id] = active["id"]

    await callback.message.edit_text(
        question_text(idx),
        reply_markup=question_keyboard(idx),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Answer handling ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("ans:"))
async def on_answer(callback: CallbackQuery):
    storage = _get_storage(callback)
    parts = callback.data.split(":")
    q_index = int(parts[1])
    value = int(parts[2])  # 0 = don't know, 1-5 = answer

    user_id = await storage.get_or_create_user(callback.from_user)
    active = await storage.get_active_assessment(user_id)
    if not active:
        await callback.answer("Начните диагностику заново с /start")
        return

    assessment_id = active["id"]
    question = QUESTIONS[q_index]

    is_unknown = value == 0
    score = value if not is_unknown else None

    await storage.save_answer(
        assessment_id=assessment_id,
        question_code=question["code"],
        category_code=question["category"],
        option_value=value if not is_unknown else None,
        score=score,
        is_unknown=is_unknown,
    )

    next_index = q_index + 1
    await storage.update_assessment_progress(assessment_id, next_index)

    # Last question — show results
    if next_index >= len(QUESTIONS):
        await _show_results(callback, storage, assessment_id)
        return

    await callback.message.edit_text(
        question_text(next_index),
        reply_markup=question_keyboard(next_index),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Back button ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("back:"))
async def on_back(callback: CallbackQuery):
    storage = _get_storage(callback)
    q_index = int(callback.data.split(":")[1])
    prev_index = q_index - 1
    if prev_index < 0:
        await callback.answer()
        return

    user_id = await storage.get_or_create_user(callback.from_user)
    active = await storage.get_active_assessment(user_id)
    if active:
        # Delete the answer for previous question so user can re-answer
        prev_question = QUESTIONS[prev_index]
        await storage.delete_answer(active["id"], prev_question["code"])
        await storage.update_assessment_progress(active["id"], prev_index)

    await callback.message.edit_text(
        question_text(prev_index),
        reply_markup=question_keyboard(prev_index),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Abort ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "abort_confirm")
async def on_abort_confirm(callback: CallbackQuery):
    await callback.message.edit_text(
        abort_confirm_text(),
        reply_markup=abort_confirm_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "abort_yes")
async def on_abort_yes(callback: CallbackQuery):
    storage = _get_storage(callback)
    user_id = await storage.get_or_create_user(callback.from_user)
    active = await storage.get_active_assessment(user_id)
    answered = active["current_question_index"] if active else 0
    if active:
        await storage.update_assessment_progress(active["id"], active["current_question_index"])

    await callback.message.edit_text(
        f"Диагностика приостановлена.\n"
        f"Прогресс сохранен ({answered} из {len(QUESTIONS)} вопросов).\n\n"
        f"Нажмите /start чтобы продолжить.",
    )
    await callback.answer()


@router.callback_query(F.data == "abort_no")
async def on_abort_no(callback: CallbackQuery):
    storage = _get_storage(callback)
    user_id = await storage.get_or_create_user(callback.from_user)
    active = await storage.get_active_assessment(user_id)
    if not active:
        await callback.answer("Нет активной диагностики.")
        return
    idx = active["current_question_index"]
    await callback.message.edit_text(
        question_text(idx),
        reply_markup=question_keyboard(idx),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Restart ───────────────────────────────────────────────────────

@router.callback_query(F.data == "restart_confirm")
async def on_restart_confirm(callback: CallbackQuery):
    await callback.message.edit_text(
        restart_confirm_text(),
        reply_markup=restart_confirm_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "restart_yes")
async def on_restart_yes(callback: CallbackQuery):
    storage = _get_storage(callback)
    user_id = await storage.get_or_create_user(callback.from_user)

    # Abandon current
    active = await storage.get_active_assessment(user_id)
    if active:
        await storage.abandon_assessment(active["id"])

    # Create new
    assessment_id = await storage.create_assessment(user_id)
    callback.bot["current_assessment"] = callback.bot.get("current_assessment", {})
    callback.bot["current_assessment"][callback.from_user.id] = assessment_id

    await callback.message.edit_text(
        question_text(0),
        reply_markup=question_keyboard(0),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "restart_no")
async def on_restart_no(callback: CallbackQuery):
    storage = _get_storage(callback)
    user_id = await storage.get_or_create_user(callback.from_user)
    active = await storage.get_active_assessment(user_id)
    if active and active["current_question_index"] > 0:
        idx = active["current_question_index"]
        await callback.message.edit_text(
            question_text(idx),
            reply_markup=question_keyboard(idx),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            welcome_text(),
            reply_markup=start_keyboard(has_progress=active is not None and active["current_question_index"] > 0),
            parse_mode="HTML",
        )
    await callback.answer()


# ── Results ───────────────────────────────────────────────────────

async def _show_results(callback: CallbackQuery, storage, assessment_id: int):
    """Calculate results, show deterministic part, then call LLM."""
    answers = await storage.get_answers(assessment_id)
    result = calculate_results(answers)

    # Save deterministic result
    await storage.complete_assessment(assessment_id, result)

    # Send deterministic result
    await callback.message.edit_text(
        result_text(result),
        reply_markup=finish_keyboard(),
        parse_mode="HTML",
    )

    # Call LLM for analysis
    await callback.message.answer("⏳ Генерирую расширенный анализ...")

    analysis = await generate_analysis(result, answers)
    if analysis:
        await storage.save_llm_analysis(assessment_id, analysis)
        # Split long messages for Telegram (4096 char limit)
        for chunk in _split_message(analysis, 4000):
            await callback.message.answer(chunk)
    else:
        fallback = get_fallback_analysis(result["maturity_level"])
        await callback.message.answer(fallback)

    await callback.answer()


def _split_message(text: str, max_len: int = 4000) -> list[str]:
    """Split text into chunks respecting line breaks."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line
    if current:
        chunks.append(current)
    return chunks
