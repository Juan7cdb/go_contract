from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "Go Contract AI"
    ENVIRONMENT: str = "local"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    
    # Security
    FRONTEND_URL: str = "http://localhost:3000"  # Change in production
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str  # Service Role Key for backend operations
    SUPABASE_JWT_SECRET: str = ""  # For local JWT validation (optional but recommended)
    
    # Google Gemini
    GOOGLE_API_KEY: str
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )

settings = Settings()
