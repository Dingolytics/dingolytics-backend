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
        "redash.query_runner.athena",
        "redash.query_runner.big_query",
        "redash.query_runner.google_spreadsheets",
        "redash.query_runner.graphite",
        "redash.query_runner.mongodb",
        "redash.query_runner.couchbase",
        "redash.query_runner.mysql",
        "redash.query_runner.pg",
        "redash.query_runner.url",
        "redash.query_runner.influx_db",
        "redash.query_runner.elasticsearch",
        "redash.query_runner.elasticsearch2",
        "redash.query_runner.amazon_elasticsearch",
        "redash.query_runner.trino",
        "redash.query_runner.presto",
        "redash.query_runner.pinot",
        "redash.query_runner.databricks",
        "redash.query_runner.hive_ds",
        "redash.query_runner.impala_ds",
        "redash.query_runner.vertica",
        "redash.query_runner.clickhouse",
        "redash.query_runner.yandex_metrica",
        "redash.query_runner.rockset",
        "redash.query_runner.treasuredata",
        "redash.query_runner.sqlite",
        "redash.query_runner.dynamodb_sql",
        "redash.query_runner.mssql",
        "redash.query_runner.mssql_odbc",
        "redash.query_runner.memsql_ds",
        "redash.query_runner.mapd",
        "redash.query_runner.jql",
        "redash.query_runner.google_analytics",
        "redash.query_runner.axibase_tsd",
        "redash.query_runner.salesforce",
        "redash.query_runner.query_results",
        "redash.query_runner.prometheus",
        "redash.query_runner.qubole",
        "redash.query_runner.db2",
        "redash.query_runner.druid",
        "redash.query_runner.kylin",
        "redash.query_runner.drill",
        "redash.query_runner.uptycs",
        "redash.query_runner.snowflake",
        "redash.query_runner.phoenix",
        "redash.query_runner.json_ds",
        "redash.query_runner.cass",
        "redash.query_runner.dgraph",
        "redash.query_runner.azure_kusto",
        "redash.query_runner.exasol",
        "redash.query_runner.cloudwatch",
        "redash.query_runner.cloudwatch_insights",
        "redash.query_runner.corporate_memory",
        "redash.query_runner.sparql_endpoint",
        "redash.query_runner.excel",
        "redash.query_runner.csv",
        "redash.query_runner.firebolt",
        "redash.query_runner.databend",
        "redash.query_runner.nz",
        "redash.query_runner.arango"
    ]
    QUERY_RUNNERS_DISABLED: List[str] = []

    @property
    def REDIS_FULL_URL(self) -> str:
        return add_decode_responses_to_redis_url(self.REDIS_URL)

    @property
    def QUERY_RUNNERS(self) -> List[str]:
        default_set = set(self.QUERY_RUNNERS_DEFAULT)
        disabled_set = set(self.QUERY_RUNNERS_DEFAULT)
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
