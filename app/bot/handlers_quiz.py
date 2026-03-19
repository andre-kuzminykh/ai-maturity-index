"""Handlers: quiz flow — displaying questions and processing answers."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import async_session
from app.db.models import Assessment, Question, Answer, Category
from app.bot.states import DiagnosticStates
from app.bot.keyboards import question_keyboard, category_complete_keyboard
from app.bot.texts import format_question, format_category_complete

router = Router()

TOTAL_QUESTIONS = 35
TOTAL_CATEGORIES = 7
QUESTIONS_PER_CATEGORY = 5


async def _get_question_by_order(session, order: int) -> Question | None:
    """Fetch question with its category and options by global order."""
    result = await session.execute(
        select(Question)
        .options(selectinload(Question.category), selectinload(Question.options))
        .where(Question.order == order, Question.is_active == True)
    )
    return result.scalars().first()


async def send_question(message: Message, state: FSMContext):
    """Send the current question to the user."""
    data = await state.get_data()
    current_order = data.get("current_order", 1)

    async with async_session() as session:
        question = await _get_question_by_order(session, current_order)
        if question is None:
            await message.edit_text("Ошибка: вопрос не найден.")
            return

        cat = question.category
        category_order = cat.order
        question_in_category = current_order - (category_order - 1) * QUESTIONS_PER_CATEGORY

        options_data = [
            {"id": opt.id, "label_short": opt.label_short, "text_full": opt.text_full, "score": opt.score}
            for opt in sorted(question.options, key=lambda o: o.order)
        ]

        text = format_question(
            category_emoji=cat.emoji,
            category_name=cat.name,
            question_order=current_order,
            total_questions=TOTAL_QUESTIONS,
            category_order=category_order,
            total_categories=TOTAL_CATEGORIES,
            question_in_category=question_in_category,
            questions_in_category=QUESTIONS_PER_CATEGORY,
            question_text=question.text,
            explanation=question.short_explanation,
            options=options_data,
        )

        kb = question_keyboard(options_data, current_order)

    try:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        # If edit fails (e.g. new message needed), send new
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("ans:"))
async def on_answer(callback: CallbackQuery, state: FSMContext):
    """Process user's answer to a question."""
    await callback.answer()

    parts = callback.data.split(":")
    # ans:{question_order}:{option_id}:{score}
    question_order = int(parts[1])
    option_id = int(parts[2])
    score = int(parts[3])
    is_unknown = option_id == 0

    data = await state.get_data()
    assessment_id = data.get("assessment_id")

    async with async_session() as session:
        # Get question by order
        question = await _get_question_by_order(session, question_order)
        if question is None:
            return

        # Check if answer already exists for this question in this assessment
        existing = await session.execute(
            select(Answer).where(
                Answer.assessment_id == assessment_id,
                Answer.question_id == question.id,
            )
        )
        answer = existing.scalars().first()

        if answer:
            # Update existing answer
            answer.option_id = None if is_unknown else option_id
            answer.score = None if is_unknown else score
            answer.is_unknown = is_unknown
        else:
            # Create new answer
            answer = Answer(
                assessment_id=assessment_id,
                question_id=question.id,
                option_id=None if is_unknown else option_id,
                score=None if is_unknown else score,
                is_unknown=is_unknown,
            )
            session.add(answer)

        # Update assessment progress
        assessment = await session.get(Assessment, assessment_id)
        if assessment:
            assessment.current_question_order = question_order + 1

        await session.commit()

    next_order = question_order + 1

    # Check if category just completed (every 5 questions)
    if question_order % QUESTIONS_PER_CATEGORY == 0 and question_order < TOTAL_QUESTIONS:
        await state.update_data(current_order=next_order)
        await state.set_state(DiagnosticStates.category_complete)

        async with async_session() as session:
            q = await _get_question_by_order(session, question_order)
            cat_name = q.category.name if q else ""
            cat_emoji = q.category.emoji if q else ""

        text = format_category_complete(cat_emoji, cat_name, question_order, TOTAL_QUESTIONS)
        await callback.message.edit_text(
            text, reply_markup=category_complete_keyboard(), parse_mode="HTML"
        )
        return

    # Check if quiz is complete
    if next_order > TOTAL_QUESTIONS:
        await state.update_data(current_order=next_order)
        await state.set_state(DiagnosticStates.results)
        from app.bot.handlers_results import show_results
        await show_results(callback.message, state)
        return

    # Show next question
    await state.update_data(current_order=next_order)
    await send_question(callback.message, state)
