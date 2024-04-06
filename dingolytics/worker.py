import logging
import sys
from typing import Any

from dingolytics.defaults import worker
from redash.settings import get_settings


def main():
    options = get_worker_consumer_options()
    consumer = worker.create_consumer(**options)
    consumer.run()


def get_worker_consumer_options() -> dict[str, Any]:
    # from huey.consumer_options import config_defaults
    # config_defaults = (
    #     ('workers', 1),
    #     ('worker_type', WORKER_THREAD),
    #     ('initial_delay', 0.1),
    #     ('backoff', 1.15),
    #     ('max_delay', 10.0),
    #     ('check_worker_health', True),
    #     ('health_check_interval', 10),
    #     ('scheduler_interval', 1),
    #     ('periodic', True),
    #     ('logfile', None),
    #     ('verbose', None),
    #     ('simple_log', None),
    #     ('flush_locks', False),
    #     ('extra_locks', None),
    # )
    return {
        "workers": 4,  # TODO: Check number of CPU cores available
        "worker_type": "thread",
    }


if __name__ == "__main__":
    settings = get_settings()
    logger = logging.getLogger('huey.consumer')
    logger.setLevel(settings.LOG_LEVEL)

    if sys.version_info >= (3, 8) and sys.platform == "darwin":
        import multiprocessing

        try:
            multiprocessing.set_start_method("fork")
        except RuntimeError:
            pass
    main()
