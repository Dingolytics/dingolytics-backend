import datetime
import logging

from flask import current_app

from dingolytics.defaults import worker
from redash import models, utils

logger = logging.getLogger(__name__)


@worker.task()
def check_alerts_for_query_task(query_id: int):
    logger.debug("Checking query %d for alerts", query_id)

    query = models.Query.query.get(query_id)

    for alert in query.alerts:
        logger.info("Checking alert (%d) of query %d.", alert.id, query_id)
        new_state = alert.evaluate()

        if should_notify(alert, new_state):
            logger.info("Alert %d new state: %s", alert.id, new_state)
            old_state = alert.state

            alert.state = new_state
            alert.last_triggered_at = utils.utcnow()
            models.db.session.commit()

            if (
                old_state == models.Alert.UNKNOWN_STATE
                and new_state == models.Alert.OK_STATE
            ):
                logger.debug(
                    "Skipping notification (previous state was unknown and now it's ok)."
                )
                continue

            if alert.muted:
                logger.debug("Skipping notification (alert muted).")
                continue

            notify_subscriptions(alert, new_state)


def notify_subscriptions(alert, new_state):
    host = utils.base_url(alert.query_rel.org)
    for subscription in alert.subscriptions:
        try:
            subscription.notify(
                alert, alert.query_rel, subscription.user, new_state, current_app, host
            )
        except Exception as exc:
            logger.exception(exc)


def should_notify(alert, new_state):
    passed_rearm_threshold = False
    if alert.rearm and alert.last_triggered_at:
        passed_rearm_threshold = (
            alert.last_triggered_at + datetime.timedelta(seconds=alert.rearm) < utils.utcnow()
        )
    return new_state != alert.state or (
        alert.state == models.Alert.TRIGGERED_STATE and passed_rearm_threshold
    )
