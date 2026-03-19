from __future__ import annotations

import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str = ""
    admin_ids: List[int] = []
    database_url: str = "sqlite+aiosqlite:///data/bot.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def db_path(self) -> str:
        """Extract SQLite file path from URL."""
        url = self.database_url
        if url.startswith("sqlite+aiosqlite:///"):
            return url.replace("sqlite+aiosqlite:///", "")
        if url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "")
        return "data/bot.db"


settings = Settings()
