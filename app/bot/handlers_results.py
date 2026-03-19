"""Handlers: results display, PDF, contact, details."""
from __future__ import annotations

import io
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import async_session
from app.db.models import Assessment, Answer, Category, User
from app.bot.states import DiagnosticStates
from app.bot.keyboards import results_keyboard, contact_keyboard
from app.bot.texts import (
    format_results_brief,
    format_results_full,
    format_category_details,
    LLM_UNAVAILABLE_TEXT,
    CONTACT_TEXT,
    CONSULT_TEXT,
)
from app.services.scoring import AssessmentResult, CategoryResult, calculate_result
from app.services.llm import get_llm_analysis

logger = logging.getLogger(__name__)

router = Router()


async def _build_result(assessment_id: int) -> tuple[AssessmentResult, str | None]:
    """Build AssessmentResult from DB data."""
    async with async_session() as session:
        # Load answers
        answers_result = await session.execute(
            select(Answer).where(Answer.assessment_id == assessment_id)
        )
        db_answers = answers_result.scalars().all()

        # Load all categories
        cats_result = await session.execute(
            select(Category).order_by(Category.order)
        )
        db_categories = cats_result.scalars().all()

        # Load assessment for user role
        assessment = await session.get(Assessment, assessment_id)
        user = await session.get(User, assessment.user_id) if assessment else None
        user_role = user.role if user else None

        # Build question_id -> category_code map
        from app.db.models import Question
        q_result = await session.execute(
            select(Question).options(selectinload(Question.category))
        )
        questions = q_result.scalars().all()
        q_cat_map = {q.id: q.category.code for q in questions}

    # Build answers list for scoring engine
    answers_data = []
    for ans in db_answers:
        cat_code = q_cat_map.get(ans.question_id, "")
        answers_data.append({
            "category_code": cat_code,
            "score": ans.score,
            "is_unknown": ans.is_unknown,
        })

    categories_data = [
        {"code": c.code, "name": c.name, "emoji": c.emoji, "weight": c.weight}
        for c in db_categories
    ]

    result = calculate_result(answers_data, categories_data)
    result.user_role = user_role
    return result, user_role


async def show_results(message: Message, state: FSMContext):
    """Calculate and display results."""
    data = await state.get_data()
    assessment_id = data.get("assessment_id")

    result, user_role = await _build_result(assessment_id)

    # Try LLM analysis
    llm_sections = await get_llm_analysis(result)

    # Save all results to DB
    async with async_session() as session:
        assessment = await session.get(Assessment, assessment_id)
        if assessment:
            from datetime import datetime, timezone
            assessment.status = "completed"
            assessment.total_score_percent = result.total_percent
            assessment.maturity_level = result.maturity_level
            assessment.reliability_level = result.reliability
            assessment.result_json = result.to_dict()
            assessment.completed_at = datetime.now(timezone.utc)
            if llm_sections:
                assessment.llm_summary = llm_sections.get("summary", "")
                assessment.llm_swot = llm_sections.get("swot", "")
                assessment.llm_recommendations = llm_sections.get("recommendations", "")
                assessment.llm_roadmap = llm_sections.get("roadmap", "")
        await session.commit()

    # Store result in state for PDF/details
    await state.update_data(
        result_dict=result.to_dict(),
        llm_sections=llm_sections,
        user_role=user_role,
    )

    # Format and send
    if llm_sections:
        text = format_results_full(result, llm_sections)
    else:
        text = format_results_brief(result) + LLM_UNAVAILABLE_TEXT

    # Telegram limit: split if needed
    if len(text) > 4096:
        text = format_results_brief(result) + "\n\n<i>Полный анализ доступен в PDF-отчёте.</i>"

    try:
        await message.edit_text(text, reply_markup=results_keyboard(), parse_mode="HTML")
    except Exception:
        await message.answer(text, reply_markup=results_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "result:pdf")
async def on_pdf(callback: CallbackQuery, state: FSMContext):
    """Generate and send PDF report."""
    await callback.answer("Генерируем PDF...")

    data = await state.get_data()
    assessment_id = data.get("assessment_id")

    result, user_role = await _build_result(assessment_id)
    llm_sections = data.get("llm_sections", {})

    try:
        from app.services.pdf import generate_pdf
        pdf_bytes = generate_pdf(result, llm_sections, user_role)
        doc = BufferedInputFile(pdf_bytes, filename="ai-maturity-report.pdf")
        await callback.message.answer_document(doc, caption="📄 Ваш отчёт по ИИ-зрелости")
    except Exception:
        logger.exception("PDF generation failed")
        await callback.message.answer("К сожалению, генерация PDF временно недоступна.")


@router.callback_query(F.data == "result:details")
async def on_details(callback: CallbackQuery, state: FSMContext):
    """Show detailed category breakdown."""
    await callback.answer()
    data = await state.get_data()
    assessment_id = data.get("assessment_id")

    result, _ = await _build_result(assessment_id)
    text = format_category_details(result)

    await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "result:contact")
async def on_contact(callback: CallbackQuery, state: FSMContext):
    """Show contact form."""
    await callback.answer()
    await state.set_state(DiagnosticStates.contact_form)
    await callback.message.edit_text(CONTACT_TEXT, reply_markup=contact_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "result:consult")
async def on_consult(callback: CallbackQuery, state: FSMContext):
    """Handle consultation request."""
    await callback.answer()
    await callback.message.answer(CONSULT_TEXT, reply_markup=contact_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "result:back")
async def on_back_to_results(callback: CallbackQuery, state: FSMContext):
    """Back to results screen."""
    await callback.answer()
    await state.set_state(DiagnosticStates.results)
    await show_results(callback.message, state)


@router.message(DiagnosticStates.contact_form)
async def on_contact_text(message: Message, state: FSMContext):
    """Save contact info from user."""
    contact_info = message.text.strip()

    data = await state.get_data()
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_user_id == message.from_user.id)
        )
        user = result.scalars().first()
        if user:
            if "@" in contact_info:
                user.email = contact_info
            else:
                user.phone = contact_info
            await session.commit()

    await message.answer(
        "✅ Спасибо! Ваши контакты сохранены. Мы свяжемся с вами.",
        reply_markup=results_keyboard(),
    )
    await state.set_state(DiagnosticStates.results)
