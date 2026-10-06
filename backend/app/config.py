from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5463/school_ops"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@127.0.0.1:5463/school_ops"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""
    TELEGRAM_SECRET_TOKEN: str = ""
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 25
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    RATE_LIMIT: str = "60/minute"
    DEFAULT_QUIET_HOURS_START: int = 21
    DEFAULT_QUIET_HOURS_END: int = 7

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
