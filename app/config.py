from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/ai_maturity"
    database_url_sync: str = "postgresql://postgres:postgres@db:5432/ai_maturity"
    redis_url: str = "redis://redis:6379/0"

    llm_api_key: str = ""
    llm_api_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    admin_secret_key: str = "change-this-secret-key"
    admin_username: str = "admin"
    admin_password: str = "admin"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
