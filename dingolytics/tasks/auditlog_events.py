import logging

import requests

from dingolytics.defaults import TaskPriority, workers
from redash import models, settings

logger = logging.getLogger(__name__)


@workers.default.task(priority=TaskPriority.top)
def record_auditlog_event_task(raw_event: dict) -> None:
    event = models.Event.record(raw_event)
    models.db.session.commit()

    for hook in settings.S.EVENT_REPORTING_WEBHOOKS:
        logger.debug("Forwarding event to: %s", hook)
        try:
            response = requests.post(hook, json={"data": event.to_dict()})
            if response.status_code != 200:
                logger.error("Failed posting to %s: %s", hook, response.content)
        except Exception:
            logger.exception("Failed posting to %s", hook)
