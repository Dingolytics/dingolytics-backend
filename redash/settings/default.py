import os
import importlib
# import ssl
from funcy import distinct, remove
from flask_talisman import talisman

from .helpers import (
    fix_assets_path,
    array_from_string,
    parse_boolean,
    int_or_none,
    set_from_string,
    add_decode_responses_to_redis_url,
    cast_int_or_default
)
from .organization import DATE_FORMAT, TIME_FORMAT  # noqa

GOOGLE_CLIENT_ID = os.environ.get("REDASH_GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("REDASH_GOOGLE_CLIENT_SECRET", "")
GOOGLE_OAUTH_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

# If Redash is behind a proxy it might sometimes receive a X-Forwarded-Proto of HTTP
# even if your actual Redash URL scheme is HTTPS. This will cause Flask to build
# the SAML redirect URL incorrect thus failing auth. This is especially common if
# you're behind a SSL/TCP configured AWS ELB or similar.
# This setting will force the URL scheme.
SAML_SCHEME_OVERRIDE = os.environ.get("REDASH_SAML_SCHEME_OVERRIDE", "")

SAML_ENCRYPTION_PEM_PATH = os.environ.get("REDASH_SAML_ENCRYPTION_PEM_PATH", "")
SAML_ENCRYPTION_CERT_PATH = os.environ.get("REDASH_SAML_ENCRYPTION_CERT_PATH", "")
SAML_ENCRYPTION_ENABLED = SAML_ENCRYPTION_PEM_PATH != "" and SAML_ENCRYPTION_CERT_PATH != ""

# If the organization setting auth_password_login_enabled is not false, then users will still be
# able to login through Redash instead of the LDAP server
LDAP_LOGIN_ENABLED = parse_boolean(os.environ.get("REDASH_LDAP_LOGIN_ENABLED", "false"))
# Bind LDAP using SSL. Default is False
LDAP_SSL = parse_boolean(os.environ.get("REDASH_LDAP_USE_SSL", "false"))
# Choose authentication method(SIMPLE, ANONYMOUS or NTLM). Default is SIMPLE
LDAP_AUTH_METHOD = os.environ.get("REDASH_LDAP_AUTH_METHOD", "SIMPLE")
# The LDAP directory address (ex. ldap://10.0.10.1:389)
LDAP_HOST_URL = os.environ.get("REDASH_LDAP_URL", None)
# The DN & password used to connect to LDAP to determine the identity of the user being authenticated.
# For AD this should be "org\\user".
LDAP_BIND_DN = os.environ.get("REDASH_LDAP_BIND_DN", None)
LDAP_BIND_DN_PASSWORD = os.environ.get("REDASH_LDAP_BIND_DN_PASSWORD", "")
# AD/LDAP email and display name keys
LDAP_DISPLAY_NAME_KEY = os.environ.get("REDASH_LDAP_DISPLAY_NAME_KEY", "displayName")
LDAP_EMAIL_KEY = os.environ.get("REDASH_LDAP_EMAIL_KEY", "mail")
# Prompt that should be shown above username/email field.
LDAP_CUSTOM_USERNAME_PROMPT = os.environ.get(
    "REDASH_LDAP_CUSTOM_USERNAME_PROMPT", "LDAP/AD/SSO username:"
)
# LDAP Search DN TEMPLATE (for AD this should be "(sAMAccountName=%(username)s)"")
LDAP_SEARCH_TEMPLATE = os.environ.get(
    "REDASH_LDAP_SEARCH_TEMPLATE", "(cn=%(username)s)"
)
# The schema to bind to (ex. cn=users,dc=ORG,dc=local)
LDAP_SEARCH_DN = os.environ.get(
    "REDASH_LDAP_SEARCH_DN", os.environ.get("REDASH_SEARCH_DN")
)

ALERTS_DEFAULT_MAIL_SUBJECT_TEMPLATE = os.environ.get(
    "REDASH_ALERTS_DEFAULT_MAIL_SUBJECT_TEMPLATE", "({state}) {alert_name}"
)

dynamic_settings = importlib.import_module(
    os.environ.get("REDASH_DYNAMIC_SETTINGS_MODULE", "redash.settings.dynamic_settings")
)

EVENT_REPORTING_WEBHOOKS = array_from_string(
    os.environ.get("REDASH_EVENT_REPORTING_WEBHOOKS", "")
)

# Client side toggles:
ALLOW_SCRIPTS_IN_USER_INPUT = parse_boolean(
    os.environ.get("REDASH_ALLOW_SCRIPTS_IN_USER_INPUT", "false")
)
DASHBOARD_REFRESH_INTERVALS = list(
    map(
        int,
        array_from_string(
            os.environ.get(
                "REDASH_DASHBOARD_REFRESH_INTERVALS", "60,300,600,1800,3600,43200,86400"
            )
        ),
    )
)
QUERY_REFRESH_INTERVALS = list(
    map(
        int,
        array_from_string(
            os.environ.get(
                "REDASH_QUERY_REFRESH_INTERVALS",
                "60, 300, 600, 900, 1800, 3600, 7200, 10800, 14400, 18000, 21600, 25200, 28800, 32400, 36000, 39600, 43200, 86400, 604800, 1209600, 2592000",
            )
        ),
    )
)
PAGE_SIZE = int(os.environ.get("REDASH_PAGE_SIZE", 20))
PAGE_SIZE_OPTIONS = list(
    map(
        int,
        array_from_string(os.environ.get("REDASH_PAGE_SIZE_OPTIONS", "5,10,20,50,100")),
    )
)
TABLE_CELL_MAX_JSON_SIZE = int(os.environ.get("REDASH_TABLE_CELL_MAX_JSON_SIZE", 50000))

# Features:
VERSION_CHECK = parse_boolean(os.environ.get("REDASH_VERSION_CHECK", "true"))
FEATURE_DISABLE_REFRESH_QUERIES = parse_boolean(
    os.environ.get("REDASH_FEATURE_DISABLE_REFRESH_QUERIES", "false")
)
FEATURE_SHOW_QUERY_RESULTS_COUNT = parse_boolean(
    os.environ.get("REDASH_FEATURE_SHOW_QUERY_RESULTS_COUNT", "true")
)
FEATURE_ALLOW_CUSTOM_JS_VISUALIZATIONS = parse_boolean(
    os.environ.get("REDASH_FEATURE_ALLOW_CUSTOM_JS_VISUALIZATIONS", "false")
)
FEATURE_AUTO_PUBLISH_NAMED_QUERIES = parse_boolean(
    os.environ.get("REDASH_FEATURE_AUTO_PUBLISH_NAMED_QUERIES", "true")
)
FEATURE_EXTENDED_ALERT_OPTIONS = parse_boolean(
    os.environ.get("REDASH_FEATURE_EXTENDED_ALERT_OPTIONS", "false")
)

# BigQuery
BIGQUERY_HTTP_TIMEOUT = int(os.environ.get("REDASH_BIGQUERY_HTTP_TIMEOUT", "600"))

# kylin
KYLIN_OFFSET = int(os.environ.get("REDASH_KYLIN_OFFSET", 0))
KYLIN_LIMIT = int(os.environ.get("REDASH_KYLIN_LIMIT", 50000))
KYLIN_ACCEPT_PARTIAL = parse_boolean(
    os.environ.get("REDASH_KYLIN_ACCEPT_PARTIAL", "false")
)

# sqlparse
SQLPARSE_FORMAT_OPTIONS = {
    "reindent": parse_boolean(os.environ.get("SQLPARSE_FORMAT_REINDENT", "true")),
    "keyword_case": os.environ.get("SQLPARSE_FORMAT_KEYWORD_CASE", "upper"),
}

# Email blocked domains, use delimiter comma to separated multiple domains
BLOCKED_DOMAINS = set_from_string(os.environ.get("REDASH_BLOCKED_DOMAINS", "qq.com"))
