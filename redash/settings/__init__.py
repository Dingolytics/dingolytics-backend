from functools import lru_cache
from typing import List
from pydantic import BaseSettings  #, ValidationError, validator

from .helpers import (
    fix_assets_path,
    array_from_string,
    parse_boolean,
    int_or_none,
    set_from_string,
    add_decode_responses_to_redis_url,
    cast_int_or_default
)
from .default import *  # noqa

__all__ = ["S"]


@lru_cache()
def get_settings() -> 'Settings':
    return Settings()


class Settings(BaseSettings):
    SECRET_KEY: str = ""
    DATASOURCE_SECRET_KEY: str = ""
    PROXIES_COUNT: int = 1

    VECTOR_INGEST_URL: str = "http://localhost:8180"

    REDIS_URL: str = "redis://localhost:6379/0"
    RQ_REDIS_URL: str = REDIS_URL

    LOG_LEVEL: str = "INFO"
    LOG_STDOUT: bool = False
    LOG_PREFIX: str = ""
    LOG_FORMAT: str = (
        LOG_PREFIX +
        "[%(asctime)s][PID:%(process)d][%(levelname)s][%(name)s] %(message)s"
    )

    STATSD_HOST: str = "localhost"
    STATSD_PORT: int = 8125
    STATSD_PREFIX: str = "redash"
    STATSD_USE_TAGS: bool = False

    RATELIMIT_ENABLED: bool = False
    THROTTLE_LOGIN_PATTERN: str = "50/hour"
    LIMITER_STORAGE: str = "memory://"
    THROTTLE_PASS_RESET_PATTERN: str = "10/hour"

    DESTINATIONS_DEFAULT: List[str] = [
        "redash.destinations.email",
        "redash.destinations.slack",
        "redash.destinations.webhook",
        "redash.destinations.hipchat",
        "redash.destinations.mattermost",
        "redash.destinations.chatwork",
        "redash.destinations.pagerduty",
        "redash.destinations.hangoutschat",
        "redash.destinations.microsoft_teams_webhook",
    ]
    DESTINATIONS_DISABLED: List[str] = []

    QUERY_RUNNERS_DEFAULT: List[str] = [
        "redash.query_runner.clickhouse",
        "redash.query_runner.pg",
        "redash.query_runner.sqlite",
    ]
    QUERY_RUNNERS_DISABLED: List[str] = []

    @property
    def REDIS_FULL_URL(self) -> str:
        return add_decode_responses_to_redis_url(self.REDIS_URL)

    @property
    def QUERY_RUNNERS(self) -> List[str]:
        default_set = set(self.QUERY_RUNNERS_DEFAULT)
        disabled_set = set(self.QUERY_RUNNERS_DISABLED)
        return list(default_set - disabled_set)

    @property
    def DESTINATIONS(self) -> List[str]:
        default_set = set(self.DESTINATIONS_DEFAULT)
        disabled_set = set(self.DESTINATIONS_DISABLED)
        return list(default_set - disabled_set)

    # @validator("SECRET_KEY")
    # def validate_secret_key(cls, v):
    #     if len(v) < 16:
    #         raise ValidationError(
    #             "SECRET_KEY must be at least 16 characters long."
    #         )
    #     return v

    # @validator("DATASOURCE_SECRET_KEY")
    # def validate_datasource_secret_key(cls, v):
    #     if len(v) < 16:
    #         raise ValidationError(
    #             "DATASOURCE_SECRET_KEY must be at least 16 characters long."
    #         )
    #     return v

    class Meta:
        env_file = ".env"


S = get_settings()
