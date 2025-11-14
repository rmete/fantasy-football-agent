from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Fantasy Football AI Manager"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "fantasy_football"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # AI/LLM
    LLM_PROVIDER: str = "anthropic"  # Options: "anthropic", "openai", "gemini"
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    # Anthropic Model Selection
    # Options: "claude-sonnet-4-5-20250929", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5-20250929"

    # Sleeper
    SLEEPER_BASE_URL: str = "https://api.sleeper.app/v1"
    SLEEPER_USERNAME: Optional[str] = None

    # External APIs (optional)
    TAVILY_API_KEY: Optional[str] = None
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "FantasyFootballAI/1.0"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
