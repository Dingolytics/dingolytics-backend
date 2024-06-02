import logging
import time

from huey import crontab
from dingolytics.defaults import workers
from dingolytics.tasks.run_query import enqueue_query_hy
from redash import models, redis_connection, settings
from redash.models.parameterized_query import (
    InvalidParameterError,
    QueryDetachedFromDataSourceError,
)
from redash.tasks.failure_report import track_failure
from redash.utils import json_dumps, sentry

logger = logging.getLogger(__name__)


class RefreshQueriesError(Exception):
    pass


@workers.periodic.task(crontab(minute='*/1'))
def refresh_queries_task():
    if settings.S.FEATURE_DISABLE_REFRESH_QUERIES:
        logger.info("Disabled refresh queries.")
        return
    logger.info("Refreshing queries...")
    enqueued = []
    for query in models.Query.outdated_queries():
        # TODO: Implement better filter for the `outdated_queries()`
        # and probably remove `_should_refresh_query` then.
        if not _should_refresh_query(query):
            continue

        try:
            query_text = _apply_default_parameters(query)
            query_text = _apply_auto_limit(query_text, query)
            enqueue_query_hy(
                query_text,
                query.data_source,
                query.user_id,
                scheduled_query=query,
                metadata={"query_id": query.id, "Username": "Scheduled"},
            )
            enqueued.append(query)
        except Exception as e:
            message = "Could not enqueue query %d due to %s" % (query.id, repr(e))
            logging.info(message)
            error = RefreshQueriesError(message).with_traceback(e.__traceback__)
            sentry.capture_exception(error)

    status = {
        "outdated_queries_count": len(enqueued),
        "last_refresh_at": time.time(),
        "query_ids": json_dumps([q.id for q in enqueued]),
    }
    redis_connection.hset("redash:status", '', '', mapping=status)
    logger.info("Done refreshing queries: %s" % status)


def _apply_default_parameters(query):
    parameters = {p["name"]: p.get("value") for p in query.parameters}
    if any(parameters):
        try:
            return query.parameterized.apply(parameters).query
        except InvalidParameterError as exc:
            track_failure(query, f"Skipping refresh of {query.id}: {exc}")
            raise
        except QueryDetachedFromDataSourceError as exc:
            track_failure(query, (
                f"Skipping refresh of {query.id} because a related dropdown "
                f"query ({exc.query_id}) is unattached to any datasource."
            ))
            raise
    else:
        return query.query_text


def _apply_auto_limit(query_text, query):
    should_apply_auto_limit = query.options.get("apply_auto_limit", False)
    return query.data_source.query_runner.apply_auto_limit(
        query_text, should_apply_auto_limit
    )


def _should_refresh_query(query):
    if query.org.is_disabled:
        logger.debug("Skipping refresh of %s because org is disabled.", query.id)
        return False
    elif query.data_source is None:
        logger.debug("Skipping refresh of %s because the datasource is none.", query.id)
        return False
    elif query.data_source.paused:
        logger.debug(
            "Skipping refresh of %s because datasource %s is paused (%s).",
            query.id,
            query.data_source.name,
            query.data_source.pause_reason,
        )
        return False
    else:
        return True
