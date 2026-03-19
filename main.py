"""
Entry point for the AI Maturity Index Telegram bot.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import settings
from bot.database import close_db, get_db
from bot.handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    if not settings.bot_token:
        logger.error("BOT_TOKEN is not set. Create a .env file with BOT_TOKEN=your-token")
        return

    # Initialize DB
    await get_db()
    logger.info("Database initialized")

    bot = Bot(token=settings.bot_token)
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook deleted, switching to polling")

    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot)
    finally:
        await close_db()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
