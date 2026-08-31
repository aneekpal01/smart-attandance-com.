import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartAttend-AI"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # SQLite Database URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./smartattend.db")
    
    # CORS Origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000"
    ]
    
    # JWT / Security (Placeholder configuration)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "smartattend-dev-secret-key-change-in-prod")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
