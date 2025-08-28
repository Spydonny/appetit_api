import os
from typing import List
from dotenv import load_dotenv

# grab env vars from .env file
load_dotenv()


class Settings:
    # app settings
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change_me_very_long")
    ACCESS_TOKEN_EXPIRES_MIN: int = int(os.getenv("ACCESS_TOKEN_EXPIRES_MIN", "1440"))

    # CORS stuff
    _origins_raw: str = os.getenv("ALLOWED_ORIGINS", "*")
    ALLOWED_ORIGINS: List[str] = [o.strip() for o in _origins_raw.split(",") if o.strip()] if _origins_raw else ["*"]

    # database config with separate creds
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "appetit")
    DB_USER: str = os.getenv("DB_USER", "appetit_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_SSL_MODE: str = os.getenv("DB_SSL_MODE", "require")
    DB_CONNECTION_TIMEOUT: int = int(os.getenv("DB_CONNECTION_TIMEOUT", "30"))
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    
    
    @property
    def DATABASE_URL(self) -> str:
        """build DATABASE_URL from individual components or use explicit override"""
        # check if DATABASE_URL is explicitly set in env (for testing)
        explicit_url = os.getenv("DATABASE_URL")
        if explicit_url:
            return explicit_url
            
        # always construct PostgreSQL URL (SQLite isn't supported)
        # allow empty password if the DB doesn't need one
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?sslmode={self.DB_SSL_MODE}&connect_timeout={self.DB_CONNECTION_TIMEOUT}"
        )

    # email stuff via Resend
    RESEND_API_KEY: str | None = os.getenv("RESEND_API_KEY")
    FROM_EMAIL: str | None = os.getenv("FROM_EMAIL")
    FROM_NAME: str = os.getenv("FROM_NAME", "APPETIT")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    EMAIL_VERIFICATION_EXPIRES_MIN: int = int(os.getenv("EMAIL_VERIFICATION_EXPIRES_MIN", "30"))
    RESEND_WEBHOOK_SECRET: str | None = os.getenv("RESEND_WEBHOOK_SECRET")

    # push notifications via Firebase
    GOOGLE_APPLICATION_CREDENTIALS: str | None = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    FCM_PROJECT_ID: str | None = os.getenv("FCM_PROJECT_ID")

    # SMS via Twilio
    TWILIO_ACCOUNT_SID: str | None = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: str | None = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_FROM_NUMBER: str | None = os.getenv("TWILIO_FROM_NUMBER")
    TWILIO_VERIFY_SERVICE_SID: str | None = os.getenv("TWILIO_VERIFY_SERVICE_SID")
    PHONE_VERIFICATION_EXPIRES_MIN: int = int(os.getenv("PHONE_VERIFICATION_EXPIRES_MIN", "10"))

    # Google Maps integration
    GOOGLE_MAPS_API_KEY_SERVER: str | None = os.getenv("GOOGLE_MAPS_API_KEY_SERVER")

    # Google Analytics 4
    GA4_MEASUREMENT_ID: str | None = os.getenv("GA4_MEASUREMENT_ID")
    GA4_API_SECRET: str | None = os.getenv("GA4_API_SECRET")

    # admin notification emails
    ADMIN_EMAILS: List[str] = [e.strip() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()]

    # POS and payment providers
    POS_PROVIDER: str = os.getenv("POS_PROVIDER", "mock")
    POS_TIMEOUT_SECONDS: int = int(os.getenv("POS_TIMEOUT_SECONDS", "5"))
    PAYMENTS_PROVIDER: str = os.getenv("PAYMENTS_PROVIDER", "mock")
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "whsec_dev")


settings = Settings()