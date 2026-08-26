import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://todo:todo@postgres:5432/login_todo")
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-this-development-secret")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))


settings = Settings()
