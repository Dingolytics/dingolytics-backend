import calendar
import datetime
import time

from redash import redis_connection, utils


def should_schedule_next(
    previous_iteration, now, interval, time=None, day_of_week=None, failures=0
):
    # if time exists then interval > 23 hours (82800s)
    # if day_of_week exists then interval > 6 days (518400s)
    if time is None:
        ttl = int(interval)
        next_iteration = previous_iteration + datetime.timedelta(seconds=ttl)
    else:
        hour, minute = time.split(":")
        hour, minute = int(hour), int(minute)

        # The following logic is needed for cases like the following:
        # - The query scheduled to run at 23:59.
        # - The scheduler wakes up at 00:01.
        # - Using naive implementation of comparing timestamps, it will skip the execution.
        normalized_previous_iteration = previous_iteration.replace(
            hour=hour, minute=minute
        )

        if normalized_previous_iteration > previous_iteration:
            previous_iteration = normalized_previous_iteration - datetime.timedelta(
                days=1
            )

        days_delay = int(interval) / 60 / 60 / 24

        days_to_add = 0
        if day_of_week is not None:
            days_to_add = (
                list(calendar.day_name).index(day_of_week)
                - normalized_previous_iteration.weekday()
            )

        next_iteration = (
            previous_iteration
            + datetime.timedelta(days=days_delay)
            + datetime.timedelta(days=days_to_add)
        ).replace(hour=hour, minute=minute)
    if failures:
        try:
            next_iteration += datetime.timedelta(minutes=2 ** failures)
        except OverflowError:
            return False
    return now > next_iteration


class ScheduledQueriesExecutions:
    KEY_NAME = "sq:executed_at"

    def __init__(self):
        self.executions = {}

    def refresh(self):
        self.executions = redis_connection.hgetall(self.KEY_NAME)

    def update(self, query_id):
        redis_connection.hset(
            self.KEY_NAME, '', 0, mapping={query_id: time.time()}
        )
        # redis_connection.hmset(self.KEY_NAME, {query_id: time.time()})

    def get(self, query_id):
        timestamp = self.executions.get(str(query_id))
        if timestamp:
            timestamp = utils.dt_from_timestamp(timestamp)

        return timestamp


scheduled_queries_executions = ScheduledQueriesExecutions()
