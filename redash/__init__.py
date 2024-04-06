import logging
import os
import sys

import redis
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from statsd import StatsClient

from . import settings
from .query_runner import import_query_runners
from .destinations import import_destinations

__all__ = [
    "redis_connection",
    "rq_redis_connection",
    "mail",
    "migrate",
    "statsd_client",
    "limiter",
]

__version__ = "0.0.15-dev"


if os.environ.get("REMOTE_DEBUG"):
    try:
        import ptvsd
        ptvsd.enable_attach(address=("0.0.0.0", 5678))
    except ImportError:
        print("Error enabling remote debugging. Make sure ptvsd is installed.")
        sys.exit(1)


def setup_logging():
    handler = logging.StreamHandler(
        sys.stdout if settings.S.LOG_STDOUT else sys.stderr
    )
    formatter = logging.Formatter(settings.S.LOG_FORMAT)
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(settings.S.LOG_LEVEL)

    # Make noisy libraries less noisy
    if settings.S.LOG_LEVEL != "DEBUG":
        for name in [
            "passlib",
            "requests.packages.urllib3",
            "snowflake.connector",
            "apiclient",
            "rq.worker",
        ]:
            logging.getLogger(name).setLevel("ERROR")


setup_logging()

redis_connection = redis.from_url(settings.S.REDIS_FULL_URL)

rq_redis_connection = redis.from_url(settings.S.RQ_REDIS_URL)

mail = Mail()

migrate = Migrate(compare_type=True)

statsd_client = StatsClient(
    host=settings.S.STATSD_HOST,
    port=settings.S.STATSD_PORT,
    prefix=settings.S.STATSD_PREFIX
)

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.S.RATELIMIT_STORAGE
)

import_query_runners(settings.S.QUERY_RUNNERS)

import_destinations(settings.S.DESTINATIONS)
