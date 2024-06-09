import logging
import time

from huey import crontab

from dingolytics.defaults import workers
from redash import models, redis_connection

logger = logging.getLogger(__name__)


@workers.periodic.periodic_task(crontab(minute='*/15'))
def refresh_all_schemas_task() -> None:
    """Refreshes the data sources schemas."""
    blacklist = [
        int(ds_id)
        for ds_id in redis_connection.smembers("data_sources:schema:blacklist")
        if ds_id
    ]
    global_start_time = time.time()

    logger.info("task=refresh_schemas state=start")

    for ds in models.DataSource.query:
        if ds.paused:
            logger.info(
                "task=refresh_schema state=skip ds_id=%s reason=paused(%s)",
                ds.id,
                ds.pause_reason,
            )
        elif ds.id in blacklist:
            logger.info(
                "task=refresh_schema state=skip ds_id=%s reason=blacklist", ds.id
            )
        elif ds.org.is_disabled:
            logger.info(
                "task=refresh_schema state=skip ds_id=%s reason=org_disabled", ds.id
            )
        else:
            refresh_schema_task(ds.id)

    logger.info(
        "task=refresh_schemas state=finish total_runtime=%.2f",
        time.time() - global_start_time,
    )


@workers.default.task(expires=120)
def refresh_schema_task(data_source_id: int) -> None:
    ds = models.DataSource.get_by_id(data_source_id)
    logger.info(u"task=refresh_schema state=start ds_id=%s", ds.id)
    start_time = time.time()
    try:
        ds.get_schema(refresh=True)
        logger.info(
            "task=refresh_schema state=finished ds_id=%s runtime=%.2f",
            ds.id,
            time.time() - start_time,
        )
        # statsd_client.incr("refresh_schema.success")
    except Exception:
        logger.warning(
            "Failed refreshing schema for the data source: %s", ds.name, exc_info=1
        )
        # statsd_client.incr("refresh_schema.error")
        logger.info(
            "task=refresh_schema state=failed ds_id=%s runtime=%.2f",
            ds.id,
            time.time() - start_time,
        )
