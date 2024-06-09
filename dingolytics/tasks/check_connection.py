import logging

from dingolytics.defaults import workers
from redash import models

logger = logging.getLogger(__name__)


@workers.default.task(expires=30)
def check_connection_task(data_source_id: int):
    logger.info("Check connection for data source - %s", data_source_id)

    try:
        data_source = models.DataSource.get_by_id(data_source_id)
        data_source.query_runner.test_connection()
        logger.info("Connection for data source %s - OK", data_source_id)
    except Exception as exc:
        return exc
    else:
        return True
