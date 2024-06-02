from flask_mail import Message
from redash import mail
from redash.models import users
from redash.worker import job, get_job_logger

logger = get_job_logger(__name__)


@job("emails")
def send_mail(to, subject, html, text):
    try:
        message = Message(recipients=to, subject=subject, html=html, body=text)

        mail.send(message)
    except Exception:
        logger.exception("Failed sending message: %s", message.subject)


def sync_user_details():
    users.sync_last_active_at()
