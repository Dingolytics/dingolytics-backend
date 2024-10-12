from typing import Any

from redash import models
from redash.settings import get_settings
from redash.handlers.base import BaseResource, get_object_or_404
from redash.permissions import require_access, require_permission, view_only


def ingest_url(self) -> str:
    host = get_settings().VECTOR_INGEST_URL
    return "{}/ingest/{}".format(host, self.ingest_key)


def _serialize(o: models.Query) -> dict[str, Any]:
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
    def get(self):
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
