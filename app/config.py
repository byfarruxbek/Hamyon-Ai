from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    telegram_bot_token: str
    # OpenRouter free route by default; OpenAI fields remain for older .env files.
    ai_api_key: str = ""
    ai_base_url: str = "https://openrouter.ai/api/v1"
    ai_model: str = "openrouter/free"
    ai_transcribe_model: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_transcribe_model: str = "whisper-1"
    database_url: str = "sqlite+aiosqlite:///./data/hamyon.db"
    timezone: str = "Asia/Tashkent"
    rate_limit_per_minute: int = 20
    monthly_spending_limit_uzs: int = 0
    reminder_hour: int = 9
    engagement_nudge_hour: int = 19
    log_level: str = "INFO"
