# from redash import models
from redash.handlers.base import BaseResource
from redash.permissions import require_permission


class EndpointListResource(BaseResource):
    @require_permission("create_query")
    def get(self):
        self.record_event({
            "action": "list",
            "object_type": "endpoint",
        })

        return []
