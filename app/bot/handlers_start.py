"""Handlers: /start, welcome screen, role selection."""
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from app.db import async_session
from app.db.models import User, Assessment
from app.bot.states import DiagnosticStates
from app.bot.keyboards import start_keyboard, role_keyboard
from app.bot.texts import WELCOME_TEXT, ROLE_TEXT

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Show welcome screen."""
    await state.clear()

    # Ensure user exists in DB
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_user_id == message.from_user.id)
        )
        user = result.scalars().first()
        if not user:
            user = User(
                telegram_user_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )
            session.add(user)
            await session.commit()

    await state.set_state(DiagnosticStates.welcome)
    await message.answer(WELCOME_TEXT, reply_markup=start_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "start_diagnostic")
async def on_start_diagnostic(callback: CallbackQuery, state: FSMContext):
    """User pressed 'Start diagnostic' — show role selection."""
    await callback.answer()
    await state.set_state(DiagnosticStates.role_selection)
    await callback.message.edit_text(ROLE_TEXT, reply_markup=role_keyboard(), parse_mode="HTML")


@router.callback_query(F.data.startswith("role:"))
async def on_role_selected(callback: CallbackQuery, state: FSMContext):
    """User selected their role — create assessment and start quiz."""
    await callback.answer()
    role = callback.data.split(":", 1)[1]

    async with async_session() as session:
        # Get user
        result = await session.execute(
            select(User).where(User.telegram_user_id == callback.from_user.id)
        )
        user = result.scalars().first()
        if user:
            user.role = role
            # Create new assessment
            assessment = Assessment(user_id=user.id, status="in_progress", current_question_order=1)
            session.add(assessment)
            await session.commit()
            await session.refresh(assessment)
            await state.update_data(assessment_id=assessment.id, current_order=1)

    await state.set_state(DiagnosticStates.quiz)

    # Trigger first question display
    from app.bot.handlers_quiz import send_question
    await send_question(callback.message, state)
