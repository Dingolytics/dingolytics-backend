from redash import settings
from advocate.exceptions import UnacceptableAddressException

__all__ = [
    "requests_session",
    "UnacceptableAddressException",
]


if settings.S.REQUESTS_PRIVATE_ADDRESS_BLOCK:
    import advocate as requests_or_advocate
else:
    import requests as requests_or_advocate


class ConfiguredSession(requests_or_advocate.Session):
    def request(self, *args, **kwargs):
        if not settings.S.REQUESTS_ALLOW_REDIRECTS:
            kwargs.update({"allow_redirects": False})
        return super().request(*args, **kwargs)


requests_session = ConfiguredSession()
