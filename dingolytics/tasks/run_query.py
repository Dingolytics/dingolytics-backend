import logging
# import signal
import time

from huey.api import Task

from dingolytics.defaults import workers, TaskPriority, TaskResult
from dingolytics.queries.errors import track_query_error
# from dingolytics.tasks.check_alerts_for_query import check_alerts_for_query_task
from redash.models import ApiUser, DataSource, Query, QueryResult, User
from redash.models.base import db
from redash.query_runner import QueryExecutionError
from redash.utils import gen_query_hash, utcnow

logger = logging.getLogger(__name__)


def enqueue_query(  # TODO: Replace older enqueue_query() with this, then rename.
    query: str,
    data_source: DataSource,
    user_id: int,
    is_api_key: bool = False,
    scheduled_query: Query | None = None,
    metadata: dict | None = None,
) -> TaskResult:
    scheduled_query_id = scheduled_query.id if scheduled_query else None
    task = run_query_task(
        query=query,
        data_source_id=data_source.id,
        user_id=user_id,
        is_api_key=is_api_key,
        scheduled_query_id=scheduled_query_id,
        metadata=metadata,
    )
    return task


@workers.default.task(priority=TaskPriority.normal, context=True)
def run_query_task(
    query: str,
    data_source_id: int,
    user_id: int,
    task: Task,  # provoded by wrapper, see `context=True`
    is_api_key: bool = False,
    scheduled_query_id: int | None = None,
    metadata: dict | None = None,
) -> int:
    """
    Execute query and return saved result ID.
    """
    metadata = metadata or {}
    user = _resolve_user(user_id, is_api_key, metadata.get("query_id", 0))
    data_source = DataSource.get_by_id(data_source_id)
    query_runner = data_source.query_runner

    # TODO: Handle 'adhoc' explicitly instead of using `scheduled_query_id`
    scheduled_query = (
        Query.get_by_id(scheduled_query_id)
        if scheduled_query_id and scheduled_query_id != "adhoc"
        else None
    )
    query_hash = gen_query_hash(query)
    started_at = time.monotonic()

    metadata.update({
        "Job ID": str(task.id),
        "Query Hash": query_hash,
        "Scheduled": bool(scheduled_query_id),
    })
    query = query_runner.annotate_query(query, metadata)

    try:
        data, error = query_runner.run_query(query, user)
    except Exception as exc:
        data, error = None, str(exc)
        logger.warning("Unexpected error while running query:", exc_info=1)

    run_time = time.monotonic() - started_at
    logger.info(
        "job=run_query_task query_hash=%s ds_id=%d data_length=%s error=[%s]",
        query_hash,
        data_source_id,
        data and len(data),
        error,
    )

    if error:
        result = QueryExecutionError(error)
        if scheduled_query:
            scheduled_query = db.session.merge(scheduled_query, load=False)
            track_query_error(scheduled_query, error)
        raise result

    query_result = QueryResult.store_result(
        org=data_source.org_id,
        data_source=data_source,
        query_hash=query_hash,
        query=query,
        data=data,
        run_time=run_time,
        retrieved_at=utcnow(),
    )

    Query.update_latest_result(query_result)
    db.session.commit()

    # for query_id in updated_query_ids:
    #     check_alerts_for_query_task(query_id)

    return query_result.id


def _resolve_user(user_id: int, is_api_key: bool, query_id: int) -> User | ApiUser | None:
    if user_id:
        if is_api_key:
            api_key = user_id
            if query_id:
                q = Query.get_by_id(query_id)
            else:
                q = Query.by_api_key(api_key)
            return ApiUser(api_key, q.org, q.groups)
        else:
            return User.get_by_id(user_id)
    else:
        return None
