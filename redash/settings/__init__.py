from functools import lru_cache
from pydantic import BaseSettings

from .default import *  # noqa


@lru_cache()
def get_settings() -> 'Settings':
    return Settings()


class Settings(BaseSettings):
    VECTOR_INGEST_URL: str = "http://localhost:8180"

    class Meta:
        env_file = ".env"
