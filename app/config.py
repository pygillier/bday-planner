import os


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    SITE_TITLE = os.environ.get("SITE_TITLE", "80 ans")

    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL")

    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
    TWILIO_API_KEY_SID = os.environ.get("TWILIO_API_KEY_SID")
    TWILIO_API_KEY_SECRET = os.environ.get("TWILIO_API_KEY_SECRET")
    TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER")
    TWILIO_REGION = os.environ.get("TWILIO_REGION")
    TWILIO_EDGE = os.environ.get("TWILIO_EDGE")

    OIDC_ISSUER = os.environ.get("OIDC_ISSUER")
    OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID")
    OIDC_CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"

    BEHIND_PROXY = os.environ.get("BEHIND_PROXY", "false").lower() == "true"


class TestConfig:
    TESTING = True
    LOG_LEVEL = "WARNING"
    SECRET_KEY = "test-secret-key"
    SITE_TITLE = "80 ans"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    RESEND_API_KEY = "test"
    RESEND_FROM_EMAIL = "Anniversaire 80 ans <test@example.com>"
    TWILIO_ACCOUNT_SID = "test-sid"
    TWILIO_AUTH_TOKEN = "test-token"
    TWILIO_API_KEY_SID = None
    TWILIO_API_KEY_SECRET = None
    TWILIO_FROM_NUMBER = "+33600000000"
    TWILIO_REGION = None
    TWILIO_EDGE = None
    OIDC_ISSUER = None
    OIDC_CLIENT_ID = None
    OIDC_CLIENT_SECRET = None
    SESSION_COOKIE_SECURE = False
