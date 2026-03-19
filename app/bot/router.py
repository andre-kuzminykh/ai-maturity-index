"""Assemble all bot routers."""
from aiogram import Router

from app.bot.handlers_start import router as start_router
from app.bot.handlers_quiz import router as quiz_router
from app.bot.handlers_results import router as results_router
from app.bot.handlers_navigation import router as nav_router


def get_main_router() -> Router:
    main_router = Router()
    main_router.include_router(start_router)
    main_router.include_router(quiz_router)
    main_router.include_router(nav_router)
    main_router.include_router(results_router)
    return main_router
