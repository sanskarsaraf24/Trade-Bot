from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────
    app_name: str = "LLM Trading System"
    app_env: str = "development"
    secret_key: str = "changeme_in_production"

    # ── Database ──────────────────────────────────────────────
    database_url: str = "postgresql://postgres:postgres@localhost:5432/trading_db"

    # ── Anthropic ─────────────────────────────────────────────
    anthropic_api_key: str = ""

    # ── SMTP ──────────────────────────────────────────────────
    smtp_host: str = "server.minpay.in"
    smtp_port: int = 587
    smtp_user: str = "info@minpay.in"
    smtp_pass: str = ""
    alert_email_from: str = "info@minpay.in"
    alert_email_to: str = ""

    # ── Broker ────────────────────────────────────────────────
    broker_type: str = "paper"  # "paper" | "zerodha" | "angel"
    zerodha_api_key: str = ""
    zerodha_api_secret: str = ""
    zerodha_totp_secret: str = ""
    angel_api_key: str = ""
    angel_client_id: str = ""
    angel_password: str = ""

    # ── JWT ───────────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
