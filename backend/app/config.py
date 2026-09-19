import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "jen_albert_paminta_estate_secret_key_2026")
    
    # Database Settings (TiDB Cloud / MySQL)
    DB_HOST = os.getenv("DB_HOST", "")
    DB_PORT = int(os.getenv("DB_PORT", "4000"))
    DB_USER = os.getenv("DB_USER", "")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "jen_paminta")
    
    # TiDB Cloud requires SSL
    DB_USE_SSL = os.getenv("DB_USE_SSL", "true").lower() in ("true", "1", "yes")

    # Business Defaults
    ESTATE_NAME = os.getenv("ESTATE_NAME", "Jen & Albert Paminta")
    CURRENCY_SYMBOL = os.getenv("CURRENCY_SYMBOL", "₱")
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

