from huey import crontab

from dingolytics.defaults import workers
from redash.models import users


@workers.periodic.periodic_task(crontab(minute='*/1'))
def sync_user_details_task():
    users.sync_last_active_at()
