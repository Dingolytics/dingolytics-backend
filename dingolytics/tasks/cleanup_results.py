import logging

from huey import crontab
from dingolytics.defaults import workers
from redash import models, settings

logger = logging.getLogger(__name__)


@workers.periodic.periodic_task(crontab(minute='*/60'))
def cleanup_unused_results_task():
    """
    Job to cleanup unused query results -- such that no query links to them
    anymore, and older than QUERY_RESULTS_CLEANUP_MAX_AGE (a week by default,
    so it's less likely to be open in someone's browser and be used).

    Each time the job deletes only QUERY_RESULTS_CLEANUP_COUNT (100 by default)
    query results so it won't choke the database in case of many such results.

    TODO: Revise query results storage strategy together with versioning.
    """
    logger.info(
        "Running query results clean up (removing maximum of %d unused "
        "results, that are %d days old or more)",
        settings.S.QUERY_RESULTS_CLEANUP_COUNT,
        settings.S.QUERY_RESULTS_CLEANUP_MAX_AGE,
    )
    unused_query_results_ids = (
        models.QueryResult.unused(settings.S.QUERY_RESULTS_CLEANUP_MAX_AGE)
        .limit(settings.S.QUERY_RESULTS_CLEANUP_COUNT)
        .with_entities(models.QueryResult.id)
        .subquery()
    )
    delete_results = models.QueryResult.query.filter(
        models.QueryResult.id.in_(unused_query_results_ids)
    ).delete(synchronize_session=False)
    models.db.session.commit()
    logger.info("Deleted %d unused query results.", delete_results)
