import datetime
import logging

from redash import models, redis_connection, settings
from redash.utils import json_dumps

logger = logging.getLogger(__name__)

__all__ = [
    "query_errors_queue_key",
    "track_query_error",
]


def query_errors_queue_key(user_id: int | str) -> str:
    return f"query_errors_queue:{user_id}"


def track_query_error(query: models.Query, error: str) -> None:
    logger.debug(error)

    query.schedule_failures += 1
    query.skip_updated_at = True
    models.db.session.add(query)
    models.db.session.commit()

    _push_to_notification_queue(error, query)


def _push_to_notification_queue(message: str, query: models.Query) -> None:
    if not query.org.get_setting("send_email_on_failed_scheduled_queries"):
        return

    if query.schedule_failures >= settings.S.MAX_FAILURE_REPORTS_PER_QUERY:
        return

    if query.user.is_disabled:
        return

    # Push error to per-user queue, notificatios are sent periodically
    # via `send_failure_report()`.
    error_data = {
        "id": query.id,
        "name": query.name,
        "message": message,
        "schedule_failures": query.schedule_failures,
        "failed_at": datetime.datetime.utcnow().strftime(
            "%B %d, %Y %I:%M%p UTC"
        ),
    }
    error_key = query_errors_queue_key(query.user.id)
    redis_connection.lpush(error_key, json_dumps(error_data))
