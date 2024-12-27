import hmac
import json
import logging
import re
from datetime import datetime, date
from typing import Dict, Any

from flask import abort, request, url_for

from redash import models
from redash.settings import get_settings
from redash.handlers.base import BaseResource, get_object_or_404
from redash.permissions import require_access, require_permission, view_only
from redash.query_runner import BaseSQLQueryRunner
from redash.security import csp_allows_embeding
from redash.utils import collect_parameters_from_request

logger = logging.getLogger(__name__)


def _serialize(o: models.Query) -> dict[str, object]:
    host = get_settings().HOST
    url = url_for(
        "endpoint_public_results", endpoint_id=o.id, token=o.api_key
    )
    return {
        "id": o.id,
        "name": o.name,
        "url": f"{host}{url}",
        "description": o.description,
        "query_text": o.query_text,
        "tags": o.tags,
        "parameters": o.parameters,
    }


def _escape_string(value: str) -> str:
    """Escape special characters in [ClickHouse] SQL string literals."""
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace("'", "\\'")
    escaped = escaped.replace("\n", "\\n")
    escaped = escaped.replace("\t", "\\t")
    escaped = escaped.replace("\b", "\\b")
    escaped = escaped.replace("\f", "\\f")
    escaped = escaped.replace("\r", "\\r")
    escaped = escaped.replace("\0", "\\0")
    return "'%s'" % escaped


def _format_value(value: Any) -> str:
    """Format different types of values for [ClickHouse] SQL."""
    if value is None:
        return "NULL"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (datetime, date)):
        return f"'{value.isoformat()}'"
    elif isinstance(value, (list, tuple)):
        return f"[{','.join(_format_value(v) for v in value)}]"
    else:
        return _escape_string(str(value))


def _validate_identifier(identifier: str) -> bool:
    """Validate that the identifier is safe to use in ClickHouse SQL."""
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier))


def _parameters_from_request(args: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract and escape parameters from Flask request arguments.
    Parameters must start with 'p_' prefix. Raises `ValueError`
    if parameter name contains invalid characters.
    """
    parameters = {}

    for key, value in args.items():
        if key.startswith("p_"):
            param_name = key[2:]  # Remove 'p_' prefix

            if not _validate_identifier(param_name):
                raise ValueError(f"Invalid parameter name: {param_name}")

            parameters[param_name] = _format_value(value)

    return parameters


class EndpointDetailsResource(BaseResource):
    @require_permission("list_data_sources")
    def get(self, endpoint_id):
        endpoint = get_object_or_404(models.Query.get_by_id, endpoint_id)
        if endpoint.is_draft:
            abort(404)
        require_access(endpoint, self.current_user, view_only)
        self.record_event({
            "action": "view",
            "object_id": endpoint.id,
            "object_type": "endpoint",
        })
        return _serialize(endpoint)


class EndpointListResource(BaseResource):
    @require_permission("create_query")
    def get(self) -> dict[str, object]:
        endpoints = models.Query.all_queries(
            self.current_user.group_ids,
            self.current_user.id,
        ).filter(models.Query.is_draft.is_(False))
        self.record_event({
            "action": "list",
            "object_type": "endpoint",
        })
        return [_serialize(o) for o in endpoints]


class EndpointPublicResultsResource(BaseResource):
    decorators = [csp_allows_embeding]

    def get(self, endpoint_id: int, token: str) -> dict[str, object]:
        endpoint: models.Query = get_object_or_404(
            models.Query.get_by_id, endpoint_id
        )

        if endpoint.is_draft or endpoint.is_archived:
            abort(403)

        if not hmac.compare_digest(token, endpoint.api_key):
            abort(403)

        try:
            args = _parameters_from_request(request.args)
        except ValueError as exc:
            abort(400, "Failed to parse parameters: %s" % str(exc))

        parameterized = endpoint.parameterized
        parameterized.apply(args)
        sql = parameterized.text

        query_runner: BaseSQLQueryRunner = endpoint.data_source.query_runner
        result_str, error = query_runner.run_query(sql, user=None)

        # Handle query error
        if error:
            logger.warning("Failed to run query: %s %s", endpoint_id, error)
            abort(400, "Failed to run query, check the parameters.")

        # Parse query results
        try:
            result = json.loads(result_str)
        except json.JSONDecodeError:
            logger.error("Failed to parse query result: %s", endpoint_id)
            abort(500, "Internal error while parsing the query result.")

        # Return the first row if available
        rows: list[dict[str, object]] = (
            result.get("rows", []) if isinstance(result, dict) else []
        )
        if not rows:
            return {}
        if len(rows) > 1:
            logger.warning(
                "One row expected from query for endpoint_id=%s, "
                "but received %d rows", endpoint_id, len(rows)
            )

        return rows[0]
