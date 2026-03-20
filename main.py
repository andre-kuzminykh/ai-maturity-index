"""Entry point for the AI Maturity Telegram bot."""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

import config
from db.models import init_db
from db.storage import Storage
from bot.handlers.assessment import router as assessment_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Set it via environment variable or in config.py")
        sys.exit(1)

    db = await init_db(config.DATABASE_PATH)
    storage = Storage(db)

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    dp = Dispatcher()
    dp.include_router(assessment_router)

    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot, storage=storage)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
