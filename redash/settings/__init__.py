from functools import lru_cache
from typing import List
from pydantic import BaseSettings  #, ValidationError, validator

from .helpers import (
    fix_assets_path,
    array_from_string,
    parse_boolean,
    int_or_none,
    set_from_string,
    add_decode_responses_to_redis_url,
    cast_int_or_default
)
from .default import *  # noqa

__all__ = ["S"]


@lru_cache()
def get_settings() -> 'Settings':
    return Settings()


class Settings(BaseSettings):
    # General settings
    HOST: str = ""
    AUTH_TYPE: str = "api_key"
    MULTI_ORG: bool = False
    SECRET_KEY: str = ""
    DATASOURCE_SECRET_KEY: str = ""
    PROXIES_COUNT: int = 1
    INVITATION_TOKEN_MAX_AGE: int = 3600 * 24 * 7
    SCHEMAS_REFRESH_SCHEDULE: int = 30
    SCHEMA_RUN_TABLE_SIZE_CALCULATIONS: bool = False
    SCHEDULED_QUERY_TIME_LIMIT: int = -1
    ADHOC_QUERY_TIME_LIMIT: int = -1
    JOB_EXPIRY_TIME: int = 3600 * 12
    JOB_DEFAULT_FAILURE_TTL: int = 3600 * 24 * 7
    SEND_FAILURE_EMAIL_INTERVAL: int = 60
    MAX_FAILURE_REPORTS_PER_QUERY: int = 100

    # Flask-Mail settings
    MAIL_SERVER: str = "localhost"
    MAIL_PORT: int = 25
    MAIL_USE_TLS: bool = False
    MAIL_USE_SSL: bool = False
    MAIL_USERNAME: str = None
    MAIL_PASSWORD: str = None
    MAIL_DEFAULT_SENDER: str = None
    MAIL_MAX_EMAILS: int = None
    MAIL_ASCII_ATTACHMENTS: bool = False

    # Cookie settings
    COOKIES_SECURE: bool = True
    REMEMBER_COOKIE_SECURE: bool = True
    REMEMBER_COOKIE_HTTPONLY: bool = True
    REMEMBER_COOKIE_DURATION: int = 3600 * 24 * 31
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_EXPIRY_TIME: int = 3600 * 6

    # CSRF protection settings
    CSRF_TIME_LIMIT: int = 3600 * 6
    CSRF_ENFORCED: bool = True

    # CORS settings
    ACCESS_CONTROL_ALLOW_ORIGIN: str = ""
    ACCESS_CONTROL_ALLOW_CREDENTIALS: bool = False
    ACCESS_CONTROL_REQUEST_METHOD: str = "GET, POST, PUT"
    ACCESS_CONTROL_ALLOW_HEADERS: str = "Content-Type"

    # SQLAlechemy settings
    SQLALCHEMY_DATABASE_URI: str = "postgresql://postgres@postgres/postgres"
    SQLALCHEMY_MAX_OVERFLOW: int = None
    SQLALCHEMY_POOL_SIZE: int = None
    SQLALCHEMY_DISABLE_POOL: bool = False
    SQLALCHEMY_ENABLE_POOL_PRE_PING: bool = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # Talisman (security) settings
    TALISMAN_ENFORCE_HTTPS: bool = False
    TALISMAN_ENFORCE_HTTPS_PERMANENT: bool = False
    TALISMAN_ENFORCE_FILE_SAVE: bool = False
    # See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Feature-Policy
    # for more information.
    TALISMAN_FEATURE_POLICY: str = ""
    # See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Referrer-Policy
    # for more information.
    TALISMAN_REFERRER_POLICY: str = "strict-origin-when-cross-origin"
    # See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Frame-Options
    # for more information.
    TALISMAN_FRAME_OPTIONS: str = "deny"
    TALISMAN_FRAME_OPTIONS_ALLOW_FROM: str = ""
    # See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security
    # for more information.
    TALISMAN_HSTS_ENABLED: bool = False
    TALISMAN_HSTS_PRELOAD: bool = False
    TALISMAN_HSTS_MAX_AGE: int = 3600 * 24 * 365
    TALISMAN_HSTS_INCLUDE_SUBDOMAINS: bool = False

    # Whether and how to send Content-Security-Policy response headers.
    # See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy
    # for more information.
    # Overriding this value via an environment variables requires setting it
    # as a string in the general CSP format of a semicolon separated list of
    # individual CSP directives, see https://github.com/GoogleCloudPlatform/flask-talisman#example-7
    # for more information. E.g.:
    CONTENT_SECURITY_POLICY: str = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-eval'; font-src 'self' data:; "
        "img-src 'self' http: https: data: blob:; object-src 'none'; "
        "frame-ancestors 'none';"
    )
    CONTENT_SECURITY_POLICY_REPORT_URI: str = ""
    CONTENT_SECURITY_POLICY_REPORT_ONLY: bool = False
    CONTENT_SECURITY_POLICY_NONCE_IN: str = ""

    # Redis client settings
    REDIS_URL: str = "redis://localhost:6379/0"
    RQ_REDIS_URL: str = REDIS_URL
    RQ_WORKER_LOG_FORMAT: str = (
        "[%(asctime)s][PID:%(process)d][%(levelname)s][%(name)s] "
        "job.func_name=%(job_func_name)s "
        "job.id=%(job_id)s %(message)s"
    )

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_STDOUT: bool = False
    LOG_PREFIX: str = ""
    LOG_FORMAT: str = (
        LOG_PREFIX +
        "[%(asctime)s][PID:%(process)d][%(levelname)s][%(name)s] %(message)s"
    )

    # Statsd client settings
    STATSD_HOST: str = "localhost"
    STATSD_PORT: int = 8125
    STATSD_PREFIX: str = "redash"
    STATSD_USE_TAGS: bool = False

    # Flask-Limiter settings
    RATELIMIT_ENABLED: bool = False
    RATELIMIT_STORAGE: str = "memory://"
    THROTTLE_LOGIN_PATTERN: str = "50/hour"
    THROTTLE_PASS_RESET_PATTERN: str = "10/hour"

    # Destinations settings
    DESTINATIONS_DEFAULT: List[str] = [
        "redash.destinations.email",
        "redash.destinations.slack",
        "redash.destinations.webhook",
        "redash.destinations.hipchat",
        "redash.destinations.mattermost",
        "redash.destinations.chatwork",
        "redash.destinations.pagerduty",
        "redash.destinations.hangoutschat",
        "redash.destinations.microsoft_teams_webhook",
    ]
    DESTINATIONS_DISABLED: List[str] = []

    # Query runners settings
    QUERY_RUNNERS_DEFAULT: List[str] = [
        "redash.query_runner.clickhouse",
        "redash.query_runner.pg",
        "redash.query_runner.sqlite",
    ]
    QUERY_RUNNERS_DISABLED: List[str] = []
    QUERY_RESULTS_CLEANUP_ENABLED: bool = True
    QUERY_RESULTS_CLEANUP_COUNT: int = 100
    QUERY_RESULTS_CLEANUP_MAX_AGE: int = 7

    # Options for HTTP requests (requests / advocate)
    REQUESTS_ALLOW_REDIRECTS: bool = True
    REQUESTS_PRIVATE_ADDRESS_BLOCK: bool = True

    # Remote login settings
    #
    # Enables the use of an externally-provided and trusted remote user
    # via an HTTP header. The "user" must be an email address.
    #
    # By default the trusted header is X-Forwarded-Remote-User.
    # You can change this by setting `REMOTE_USER_HEADER``.
    #
    # Enabling this authentication method is *potentially dangerous*, and it is
    # your responsibility to ensure that only a trusted frontend (usually on the
    # same server) can talk to the redash backend server, otherwise people will be
    # able to login as anyone they want by directly talking to the redash backend.
    # You must *also* ensure that any special header in the original request is
    # removed or always overwritten by your frontend, otherwise your frontend may
    # pass it through to the backend unchanged.
    #
    # Note that redash will only check the remote user once, upon the first need
    # for a login, and then set a cookie which keeps the user logged in.  Dropping
    # the remote user header after subsequent requests won't automatically log the
    # user out.  Doing so could be done with further work, but usually it's
    # unnecessary.
    #
    # If you also set the organization setting auth_password_login_enabled to false,
    # then your authentication will be seamless.  Otherwise a link will be presented
    # on the login page to trigger remote user auth.
    REMOTE_USER_LOGIN_ENABLED: bool = False
    REMOTE_USER_HEADER: str = "X-Forwarded-Remote-User"

    # Support for Sentry (https://getsentry.com/).
    # Just set your Sentry DSN to enable it:
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = ""

    # Vector settings
    VECTOR_INGEST_URL: str = "http://localhost:8180"

    @property
    def REDIS_FULL_URL(self) -> str:
        return add_decode_responses_to_redis_url(self.REDIS_URL)

    @property
    def QUERY_RUNNERS(self) -> List[str]:
        default_set = set(self.QUERY_RUNNERS_DEFAULT)
        disabled_set = set(self.QUERY_RUNNERS_DISABLED)
        return list(default_set - disabled_set)

    @property
    def DESTINATIONS(self) -> List[str]:
        default_set = set(self.DESTINATIONS_DEFAULT)
        disabled_set = set(self.DESTINATIONS_DISABLED)
        return list(default_set - disabled_set)

    # @validator("SECRET_KEY")
    # def validate_secret_key(cls, v):
    #     if len(v) < 16:
    #         raise ValidationError(
    #             "SECRET_KEY must be at least 16 characters long."
    #         )
    #     return v

    # @validator("DATASOURCE_SECRET_KEY")
    # def validate_datasource_secret_key(cls, v):
    #     if len(v) < 16:
    #         raise ValidationError(
    #             "DATASOURCE_SECRET_KEY must be at least 16 characters long."
    #         )
    #     return v

    class Meta:
        env_file = ".env"

    def email_configured(self) -> bool:
        return self.MAIL_DEFAULT_SENDER is not None


S = get_settings()
