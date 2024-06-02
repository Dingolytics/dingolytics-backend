import logging
import sys
from argparse import ArgumentParser
from typing import Any

from dingolytics.defaults import workers
from redash.app import create_app
from redash.settings import get_settings

# Discover all tasks by importing them:
from .tasks.check_alerts_for_query import check_alerts_for_query_task  # noqa: F401
from .tasks.check_connection import check_connection_task  # noqa: F401
from .tasks.cleanup_results import cleanup_unused_results_task  # noqa: F401
from .tasks.empty_schedules import empty_schedules_task  # noqa: F401
from .tasks.get_schema import get_schema_task  # noqa: F401
from .tasks.refresh_queries import refresh_queries_task  # noqa: F401
from .tasks.refresh_schemas import (
    refresh_all_schemas_task,  # noqa: F401
    refresh_schema_task,  # noqa: F401
)
from .tasks.run_query import run_query_task  # noqa: F401

__all__ = [
    # Discovered tasks
    "check_alerts_for_query_task",
    "check_connection_task",
    "cleanup_unused_results_task",
    "get_schema_task",
    "refresh_queries_task",
    "refresh_all_schemas_task",
    "refresh_schema_task",
    "run_query_task",

    # Main entry point
    "main",
]

app = None


def main(_type: str) -> None:
    global app

    known_workers = {
        "default": workers.default,
        "periodic": workers.periodic,
    }
    assert _type in known_workers, \
        f"Error: invalid worker '{_type}', available: {list(workers.keys())}"

    app = create_app()
    worker = known_workers[_type]
    options = get_worker_consumer_options()
    consumer = worker.create_consumer(**options)
    consumer.run()


@workers.default.pre_execute()
def pre_execute_hook(task):
    app_ctx = app.app_context()
    app_ctx.push()
    setattr(task, "_app_ctx", app_ctx)


@workers.default.post_execute()
def post_execute_hook(task, task_value, exc):
    app_ctx = getattr(task, "_app_ctx", None)
    if app_ctx:
        app_ctx.pop()


def get_worker_consumer_options() -> dict[str, Any]:
    """Get options for Huey tasks consumer."""
    # Refer to the `huey.consumer.Consumer` class
    # workers=1, periodic=True, initial_delay=0.1,
    # backoff=1.15, max_delay=10.0, scheduler_interval=1,
    # worker_type=WORKER_THREAD, check_worker_health=True,
    # health_check_interval=10, flush_locks=False,
    # extra_locks=None
    return {
        "workers": 4,  # TODO: Check number of CPU cores available
        "worker_type": "thread",
    }


if __name__ == "__main__":
    settings = get_settings()
    logger = logging.getLogger("huey.consumer")
    logger.setLevel(settings.LOG_LEVEL)

    parser = ArgumentParser()
    parser.add_argument("type", nargs="?", default="default")
    args = parser.parse_args()

    if sys.version_info >= (3, 8) and sys.platform == "darwin":
        import multiprocessing

        try:
            multiprocessing.set_start_method("fork")
        except RuntimeError:
            pass

    main(args.type)
