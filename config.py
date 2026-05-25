import os
from datetime import timedelta


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=72)
    SESSION_REFRESH_EACH_REQUEST = True


class DevelopmentConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///ramtime.db"
    )
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SERVER_NAME = "localhost.localdomain"
    # Disable bcrypt cost for faster tests
    BCRYPT_LOG_ROUNDS = 4


class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///ramtime.db")
    DEBUG = False
    # Set SESSION_COOKIE_SECURE=True only when behind an HTTPS reverse proxy.
    # Leaving it False here so plain-HTTP Docker deployments work out of the box.
    SESSION_COOKIE_SECURE = os.environ.get("HTTPS", "false").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    @classmethod
    def validate(cls) -> None:
        if not os.environ.get("SECRET_KEY"):
            raise RuntimeError(
                "SECRET_KEY environment variable must be set in production."
            )


config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
