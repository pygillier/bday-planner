import os


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL")

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
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    RESEND_API_KEY = "test"
    RESEND_FROM_EMAIL = "Anniversaire 80 ans <test@example.com>"
    OIDC_ISSUER = None
    OIDC_CLIENT_ID = None
    OIDC_CLIENT_SECRET = None
    SESSION_COOKIE_SECURE = False
