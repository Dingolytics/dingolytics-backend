import logging

from flask_mail import Message

from dingolytics.defaults import workers
from redash import mail

logger = logging.getLogger(__name__)


# TODO: Use separate worker for notifications (emails and other channels).
@workers.default.task()
def send_mail_task(to: list, subject: str, html: str, text: str) -> None:
    try:
        message = Message(recipients=to, subject=subject, html=html, body=text)
        mail.send(message)
    except Exception:
        logger.exception("Failed sending message: %s", message.subject)
