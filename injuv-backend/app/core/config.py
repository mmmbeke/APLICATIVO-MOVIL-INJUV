from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "INJUV Mobile API"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str
    DB_SSLMODE: str = "require"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    CORS_ORIGINS: Annotated[list[str], NoDecode] = ["*"]

    PASSWORD_HASH_SCHEME: str = "werkzeug"

    NOTICIAS_IMAGEN_BASE_URL: str = "https://plataforma-web-injuv.onrender.com/api/noticias/imagen/"

    # Zona horaria usada para interpretar fechas sin offset enviadas por los clientes
    TIMEZONE: str = "America/Santiago"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str) and not v.strip().startswith("["):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("PASSWORD_HASH_SCHEME")
    @classmethod
    def _check_scheme(cls, v: str) -> str:
        v = v.lower()
        if v not in {"werkzeug", "bcrypt"}:
            raise ValueError("PASSWORD_HASH_SCHEME debe ser 'werkzeug' o 'bcrypt'")
        return v

    @property
    def sqlalchemy_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg2://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
