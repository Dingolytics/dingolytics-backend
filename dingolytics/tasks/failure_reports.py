import logging
import re
from collections import Counter

from huey import crontab

from dingolytics.defaults import workers
from dingolytics.queries.errors import query_errors_queue_key
from dingolytics.tasks.send_email import send_mail_task
from redash import models, redis_connection, settings
from redash.utils import base_url, json_loads, render_template

logger = logging.getLogger(__name__)


@workers.periodic.periodic_task(crontab(minute='*/60'))
def send_aggregated_failure_reports_task() -> None:
    # TODO: Configuring per-organization would be nice. So we'd need
    # to try every minute and check per-organization queues.
    for k in redis_connection.scan_iter(query_errors_queue_key("*")):
        user_id = re.search(r"\d+", k).group()
        _send_failure_report(user_id)


def _send_failure_report(user_id: str) -> None:
    user = models.User.get_by_id(user_id)
    errors_key = query_errors_queue_key(user_id)
    errors_raw = redis_connection.lrange(errors_key, 0, -1)

    if not errors_raw:
        return

    errors = [json_loads(e) for e in reversed(errors_raw)]

    occurrences = Counter((e.get("id"), e.get("message")) for e in errors)
    unique_errors = {(e.get("id"), e.get("message")): e for e in errors}
    errors_count = len(unique_errors.keys())

    subject = f"Failed to execute {errors_count} of your scheduled queries"
    context = {
        "failures": [
            {
                "id": v.get("id"),
                "name": v.get("name"),
                "failed_at": v.get("failed_at"),
                "failure_reason": v.get("message"),
                "failure_count": occurrences[k],
                "comment": _comment_for(v),
            }
            for k, v in unique_errors.items()
        ],
        "base_url": base_url(user.org),
    }
    html, text = [
        render_template(f"emails/failures.{fmt}", context)
        for fmt in ["html", "txt"]
    ]

    # TODO: Use alerts channels to send aggregated reports as well,
    # not just the hardcoded email notifications.
    send_mail_task([user.email], subject, html, text)

    # TODO: Use more reliable cleanup, e.g. new errors might be added while
    # processing the current errors queue.
    redis_connection.delete(errors_key)


def _comment_for(failure: dict) -> str:
    schedule_failures = failure.get("schedule_failures")
    if schedule_failures > settings.S.MAX_FAILURE_REPORTS_PER_QUERY * 0.75:
        return """NOTICE: This query has failed a total of {schedule_failures} times.
        Reporting may stop when the query exceeds {max_failure_reports} overall failures.""".format(
            schedule_failures=schedule_failures,
            max_failure_reports=settings.S.MAX_FAILURE_REPORTS_PER_QUERY,
        )
