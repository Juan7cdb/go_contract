from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
from typing import Optional

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "Go Contract AI"
    ENVIRONMENT: str = "local"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    
    # Security
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: str = "http://localhost:5173,https://go-contract-frontend.vercel.app,https://app.gocontract.us,https://www.gocontract.us"
    ALLOWED_ORIGIN_REGEX: Optional[str] = r"https://(.*\.vercel\.app|.*\.gocontract\.us)"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, list):
            return ",".join(v)
        return v or "http://localhost:5173,https://go-contract-frontend.vercel.app,https://app.gocontract.us"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    DATABASE_URL: str

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    
    # OpenAI
    OPENAI_API_KEY: str

    # Email
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "onboarding@resend.dev"
    GMAIL_USER: str = ""
    GMAIL_APP_PASSWORD: str = ""
    PASSWORD_RESET_EXPIRE_MINUTES: int = 60

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 20

    # Object Storage (S3-compatible, Railway portable-trunk)
    AWS_ENDPOINT_URL: str = ""
    AWS_DEFAULT_REGION: str = "auto"
    AWS_S3_BUCKET_NAME: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AVATAR_URL_TTL_SECONDS: int = 3600

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_API_VERSION: str = "2024-11-20.acacia"
    # Stripe redirect URLs. If empty, defaults are derived from FRONTEND_URL
    # in the post-init validator below.
    STRIPE_SUCCESS_URL: str = ""
    STRIPE_CANCEL_URL: str = ""

    @model_validator(mode="after")
    def _set_stripe_default_urls(self):
        if not self.STRIPE_SUCCESS_URL:
            self.STRIPE_SUCCESS_URL = (
                f"{self.FRONTEND_URL}/billing/success"
                "?session_id={CHECKOUT_SESSION_ID}"
            )
        if not self.STRIPE_CANCEL_URL:
            self.STRIPE_CANCEL_URL = f"{self.FRONTEND_URL}/billing/cancel"
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )

settings = Settings()
