import json
import logging

from flask import request
from flask_restful import abort

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
    return {
        "id": o.id,
        "name": o.name,
        "url": f"{host}/.../",
        "description": o.description,
        "query_text": o.query_text,
        "tags": o.tags,
        "parameters": o.parameters,
    }


class EndpointDetailsResource(BaseResource):
    @require_permission("list_data_sources")
    def get(self, endpoint_id):
        endpoint = get_object_or_404(models.Query.get_by_id, endpoint_id)
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
            include_drafts=False,
        )
        self.record_event({
            "action": "list",
            "object_type": "endpoint",
        })
        return [_serialize(o) for o in endpoints]


class EndpointPublicResultsResource(BaseResource):
    decorators = BaseResource.decorators + [csp_allows_embeding]

    def get(self, endpoint_id: int, token: str) -> dict[str, object]:
        endpoint = get_object_or_404(models.Query.by_api_key, token)
        parameterized = endpoint.parameterized
        parameterized.apply(collect_parameters_from_request(request.args))

        query_runner: BaseSQLQueryRunner = endpoint.data_source.query_runner
        query_sql = parameterized.text
        result_str, error = query_runner.run_query(query_sql, user=None)

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
                "but received %d rows", endpoint_id, len(rows))

        return rows[0]
