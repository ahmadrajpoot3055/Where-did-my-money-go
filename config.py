import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Ensure instance folder exists
(BASE_DIR / "instance").mkdir(parents=True, exist_ok=True)

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-fallback-secret-key-super-secure-change-in-prod-12345")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)) # 10 MB
    
    # Private storage paths
    UPLOAD_FOLDER = BASE_DIR / os.environ.get("UPLOAD_FOLDER", "private_uploads")
    ML_ARTIFACTS_FOLDER = BASE_DIR / os.environ.get("ML_ARTIFACTS_FOLDER", "ml_artifacts")
    
    # Security & session
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    
    # Defaults
    DEFAULT_CURRENCY = os.environ.get("DEFAULT_CURRENCY", "PKR")
    DEFAULT_TIMEZONE = os.environ.get("DEFAULT_TIMEZONE", "Asia/Karachi")

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'finance_app.db'}"
    )

class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
