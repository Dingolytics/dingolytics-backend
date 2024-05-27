import logging

from dingolytics.defaults import workers
from huey import crontab
from redash import models

logger = logging.getLogger(__name__)


@workers.periodic.task(crontab(minute='*/60'))
def empty_schedules_task():
    logger.info("Deleting schedules of past scheduled queries...")

    queries = models.Query.past_scheduled_queries()
    for query in queries:
        query.schedule = {}
    models.db.session.commit()

    logger.info("Deleted %d schedules.", len(queries))
