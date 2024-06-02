from functools import lru_cache
from typing import Any, Dict, List, Protocol

from pydantic import BaseSettings, PyObject, root_validator

from ._helpers import (
    add_decode_responses_to_redis_url,
    fix_assets_path,
    parse_boolean,
)

__all__ = [
    "S",  # Default global settings
    "D",  # Dynamic settings module
    "get_settings",
    # Helpers
    "parse_boolean",
    "fix_assets_path",
    "add_decode_responses_to_redis_url",
]


class DynamicSettingsProtocol(Protocol):
    # PostgreSQL extensions to use for the main database
    database_extensions: list[str]

    # Reference implementation: redash.models.DBPersistence
    QueryResultPersistence: Any = None

    def query_time_limit(
        self, is_scheduled: bool, user_id: int, org_id: int
    ) -> int:
        pass

    def periodic_jobs(self) -> list[dict[str, Any]]:
        pass

    def ssh_tunnel_auth(self) -> dict:
        pass

    def database_key_definitions(self, default: dict) -> dict[str, Any]:
        pass

    def setup_default_org(self, name: str) -> tuple[Any, list[Any]]:
        pass

    def setup_default_user(
        self,
        *,
        org: Any,
        group_ids: List[int],
        name: str,
        email: str,
        password: str,
        **kwargs,
    ) -> Any:
        pass


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
    ALERTS_DEFAULT_MAIL_SUBJECT_TEMPLATE: str = "({state}) {alert_name}"
    EVENT_REPORTING_WEBHOOKS: List[str] = []
    BLOCKED_DOMAINS: List[str] = ["qq.com"]
    DYNAMIC_SETTINGS: PyObject = "dingolytics.defaults.DynamicSettings"

    # Vector settings
    VECTOR_INGEST_URL: str = "http://localhost:8180"

    # Format settings
    FORMAT_DATE: str = "DD/MM/YY"
    FORMAT_TIME: str = "HH:mm"
    FORMAT_INTEGER: str = "0,0"
    FORMAT_FLOAT: str = "0,0.00"

    # SQL parser settings
    SQLPARSE_FORMAT_OPTIONS: Dict[str, Any] = {
        "reindent": True,
        "keyword_case": "upper",
    }

    # Client side options
    ALLOW_SCRIPTS_IN_USER_INPUT: bool = False
    DASHBOARD_REFRESH_INTERVALS: List[int] = [
        30,
        60,
        300,
        600,
        1800,
        3600,
        43200,
        86400,
    ]
    QUERY_REFRESH_INTERVALS: List[int] = [
        60,
        300,
        600,
        900,
        1800,
        3600,
        7200,
        10800,
        14400,
        18000,
        21600,
        25200,
        28800,
        32400,
        36000,
        39600,
        43200,
        86400,
        604800,
        1209600,
        2592000,
    ]
    PAGE_SIZE_DEFAULT: int = 20
    PAGE_SIZE_OPTIONS: List[int] = [5, 10, 20, 50, 100]
    TABLE_CELL_MAX_JSON_SIZE: int = 50000

    # Features settings
    FEATURE_DISABLE_REFRESH_QUERIES: bool = False
    FEATURE_SHOW_QUERY_RESULTS_COUNT: bool = True
    FEATURE_ALLOW_CUSTOM_JS_VISUALIZATIONS: bool = False
    FEATURE_AUTO_PUBLISH_NAMED_QUERIES: bool = True
    FEATURE_EXTENDED_ALERT_OPTIONS: bool = False
    FEATURE_SHOW_PERMISSIONS_CONTROL: bool = False
    FEATURE_MULTI_BYTE_SEARCH: bool = False
    FEATURE_SEND_EMAIL_ON_FAILED_SCHEDULED_QUERIES: bool = False
    FEATURE_HIDE_PLOTLY_MODE_BAR: bool = False
    FEATURE_DISABLE_PUBLIC_URLS: bool = False

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

    # Flask-Login cookie settings
    # https://flask-login.readthedocs.io/en/latest/#cookie-settings
    REMEMBER_COOKIE_SECURE: bool = True
    REMEMBER_COOKIE_HTTPONLY: bool = True
    REMEMBER_COOKIE_DURATION: int = 3600 * 24 * 31

    # Flask session settings
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
    RQ_REDIS_URL: str = ""
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
        LOG_PREFIX
        + "[%(asctime)s][PID:%(process)d][%(levelname)s][%(name)s] %(message)s"
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

    # Password login settings
    PASSWORD_LOGIN_ENABLED: bool = True

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

    # JWT settings
    JWT_LOGIN_ENABLED: bool = False
    JWT_AUTH_ISSUER: str = ""
    JWT_AUTH_PUBLIC_CERTS_URL: str = ""
    JWT_AUTH_AUDIENCE: str = ""
    JWT_AUTH_ALGORITHMS: List[str] = ["HS256", "RS256", "ES256"]
    JWT_AUTH_COOKIE_NAME: str = ""
    JWT_AUTH_HEADER_NAME: str = ""

    # SAML settings
    SAML_SCHEME_OVERRIDE: str = ""
    SAML_ENCRYPTION_PEM_PATH: str = ""
    SAML_ENCRYPTION_CERT_PATH: str = ""
    SAML_ENCRYPTION_ENABLED = False

    # Google OAuth settings
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_OAUTH_ENABLED: bool = False

    # LDAP settings
    # If the organization setting auth_password_login_enabled is not false,
    # then users will still be able to login through Redash instead of
    # the LDAP server.
    LDAP_LOGIN_ENABLED: bool = False
    LDAP_SSL: bool = False
    # Choose authentication method(SIMPLE, ANONYMOUS or NTLM).
    LDAP_AUTH_METHOD: str = "SIMPLE"
    # The LDAP directory address (ex. ldap://10.0.10.1:389)
    LDAP_HOST_URL: str = None
    LDAP_BIND_DN: str = None
    LDAP_BIND_DN_PASSWORD: str = ""
    LDAP_DISPLAY_NAME_KEY: str = "displayName"
    LDAP_EMAIL_KEY: str = "mail"
    LDAP_CUSTOM_USERNAME_PROMPT: str = "LDAP/AD/SSO username:"
    LDAP_SEARCH_TEMPLATE: str = "(cn=%(username)s)"
    LDAP_SEARCH_DN: str = None

    # SAML settings
    SAML_LOGIN_TYPE: str = ""
    SAML_METADATA_URL: str = ""
    SAML_ENTITY_ID: str = ""
    SAML_NAMEID_FORMAT: str = ""
    SAML_SSO_URL: str = ""
    SAML_X509_CERT: str = ""
    SAML_SP_SETTINGS: str = ""

    # Support for Sentry (https://getsentry.com/).
    # Just set your Sentry DSN to enable it:
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = ""

    # BigQuery client settings
    BIGQUERY_HTTP_TIMEOUT: int = 600

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

    @property
    def SAML_LOGIN_ENABLED(self) -> bool:
        if self.SAML_LOGIN_TYPE == "static":
            return bool(self.SAML_SSO_URL and self.SAML_METADATA_URL)
        else:
            return bool(self.SAML_METADATA_URL)

    @root_validator(allow_reuse=True)
    def validate_RQ_REDIS_URL(cls, values) -> dict:
        if not values.get("RQ_REDIS_URL"):
            values["RQ_REDIS_URL"] = values["REDIS_URL"]
        return values

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

    class Config:
        env_file = ".env"

    def email_configured(self) -> bool:
        return self.MAIL_DEFAULT_SENDER is not None

    def org_settings(self) -> dict:
        return {
            "beacon_consent": None,
            "auth_password_login_enabled": self.PASSWORD_LOGIN_ENABLED,
            "auth_saml_enabled": self.SAML_LOGIN_ENABLED,
            "auth_saml_type": self.SAML_LOGIN_TYPE,
            "auth_saml_entity_id": self.SAML_ENTITY_ID,
            "auth_saml_metadata_url": self.SAML_METADATA_URL,
            "auth_saml_nameid_format": self.SAML_NAMEID_FORMAT,
            "auth_saml_sso_url": self.SAML_SSO_URL,
            "auth_saml_x509_cert": self.SAML_X509_CERT,
            "auth_saml_sp_settings": self.SAML_SP_SETTINGS,
            "date_format": self.FORMAT_DATE,
            "time_format": self.FORMAT_TIME,
            "integer_format": self.FORMAT_INTEGER,
            "float_format": self.FORMAT_FLOAT,
            "auth_jwt_login_enabled": self.JWT_LOGIN_ENABLED,
            "auth_jwt_auth_issuer": self.JWT_AUTH_ISSUER,
            "auth_jwt_auth_public_certs_url": self.JWT_AUTH_PUBLIC_CERTS_URL,
            "auth_jwt_auth_audience": self.JWT_AUTH_AUDIENCE,
            "auth_jwt_auth_algorithms": self.JWT_AUTH_ALGORITHMS,
            "auth_jwt_auth_cookie_name": self.JWT_AUTH_COOKIE_NAME,
            "auth_jwt_auth_header_name": self.JWT_AUTH_HEADER_NAME,
            "multi_byte_search_enabled": self.FEATURE_MULTI_BYTE_SEARCH,
            "feature_show_permissions_control": self.FEATURE_SHOW_PERMISSIONS_CONTROL,
            "send_email_on_failed_scheduled_queries": self.FEATURE_SEND_EMAIL_ON_FAILED_SCHEDULED_QUERIES,
            "hide_plotly_mode_bar": self.FEATURE_HIDE_PLOTLY_MODE_BAR,
            "disable_public_urls": self.FEATURE_DISABLE_PUBLIC_URLS,
        }


@lru_cache()
def get_settings() -> "Settings":
    return Settings()


S: Settings = get_settings()

D: DynamicSettingsProtocol = S.DYNAMIC_SETTINGS()
