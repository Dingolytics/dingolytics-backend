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
