"""Handlers: navigation — back, stop, restart, continue."""
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import select

from app.db import async_session
from app.db.models import Assessment, Answer
from app.bot.states import DiagnosticStates
from app.bot.keyboards import confirm_stop_keyboard, confirm_restart_keyboard, start_keyboard
from app.bot.texts import STOP_CONFIRM_TEXT, RESTART_CONFIRM_TEXT, WELCOME_TEXT

router = Router()


@router.callback_query(F.data == "nav:back")
async def on_back(callback: CallbackQuery, state: FSMContext):
    """Go back to previous question."""
    await callback.answer()
    data = await state.get_data()
    current_order = data.get("current_order", 1)
    if current_order > 1:
        current_order -= 1
        await state.update_data(current_order=current_order)

    await state.set_state(DiagnosticStates.quiz)
    from app.bot.handlers_quiz import send_question
    await send_question(callback.message, state)


@router.callback_query(F.data == "nav:stop")
async def on_stop(callback: CallbackQuery, state: FSMContext):
    """Show stop confirmation."""
    await callback.answer()
    await state.set_state(DiagnosticStates.confirm_stop)
    await callback.message.edit_text(
        STOP_CONFIRM_TEXT, reply_markup=confirm_stop_keyboard(), parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm:stop_yes")
async def on_stop_confirmed(callback: CallbackQuery, state: FSMContext):
    """User confirmed stop."""
    await callback.answer()
    data = await state.get_data()
    assessment_id = data.get("assessment_id")

    if assessment_id:
        async with async_session() as session:
            assessment = await session.get(Assessment, assessment_id)
            if assessment:
                assessment.status = "abandoned"
                await session.commit()

    await state.clear()
    await callback.message.edit_text(
        "Диагностика приостановлена. Ваш прогресс сохранён.\n\nНажмите /start чтобы начать заново.",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "confirm:stop_no")
async def on_stop_cancelled(callback: CallbackQuery, state: FSMContext):
    """User cancelled stop — resume quiz."""
    await callback.answer()
    await state.set_state(DiagnosticStates.quiz)
    from app.bot.handlers_quiz import send_question
    await send_question(callback.message, state)


@router.callback_query(F.data == "nav:continue")
async def on_continue(callback: CallbackQuery, state: FSMContext):
    """Continue to next category."""
    await callback.answer()
    await state.set_state(DiagnosticStates.quiz)
    from app.bot.handlers_quiz import send_question
    await send_question(callback.message, state)


@router.callback_query(F.data == "nav:restart")
async def on_restart(callback: CallbackQuery, state: FSMContext):
    """Show restart confirmation."""
    await callback.answer()
    await state.set_state(DiagnosticStates.confirm_restart)
    await callback.message.edit_text(
        RESTART_CONFIRM_TEXT, reply_markup=confirm_restart_keyboard(), parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm:restart_yes")
async def on_restart_confirmed(callback: CallbackQuery, state: FSMContext):
    """User confirmed restart — clear and start over."""
    await callback.answer()
    data = await state.get_data()
    assessment_id = data.get("assessment_id")

    if assessment_id:
        async with async_session() as session:
            assessment = await session.get(Assessment, assessment_id)
            if assessment:
                assessment.status = "abandoned"
                await session.commit()

    await state.clear()
    await state.set_state(DiagnosticStates.welcome)
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=start_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "confirm:restart_no")
async def on_restart_cancelled(callback: CallbackQuery, state: FSMContext):
    """User cancelled restart — back to results or quiz."""
    await callback.answer()
    data = await state.get_data()
    current_order = data.get("current_order", 1)

    if current_order > 35:
        await state.set_state(DiagnosticStates.results)
        from app.bot.handlers_results import show_results
        await show_results(callback.message, state)
    else:
        await state.set_state(DiagnosticStates.quiz)
        from app.bot.handlers_quiz import send_question
        await send_question(callback.message, state)
