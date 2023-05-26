from flask import request
from flask_restful import abort
from sqlalchemy.exc import IntegrityError

from redash import models
from redash.handlers.base import (
    BaseResource,
    get_object_or_404,
    require_fields
)
from redash.permissions import (
    require_admin,
    require_permission,
)


class StreamListResource(BaseResource):
    @require_permission("list_data_sources")
    def get(self):
        if self.current_user.has_permission("admin"):
            data_sources = models.DataSource.all(self.current_org)
        else:
            data_sources = models.DataSource.all(
                self.current_org, group_ids=self.current_user.group_ids
            )

        data_sources_ids = [ds.id for ds in data_sources]
        streams = models.Stream.query.filter(
            models.Stream.data_source_id.in_(data_sources_ids)
        )

        self.record_event(
            {
                "action": "list",
                "object_type": "stream",
            }
        )

        return sorted(
            list(map(lambda x: x.to_dict(), streams)),
            key=lambda x: x["data_source_id"]
        )

    @require_admin
    def post(self):
        req = request.get_json(True)

        require_fields(req, ("data_source_id", "db_table", "name"))

        data_source = get_object_or_404(
            models.DataSource.get_by_id_and_org,
            req.get("data_source_id"), self.current_org
        )

        # TODO: Define `db_create_query` through table schema selection
        # from pre-defined list of options.

        try:
            stream = models.Stream(
                data_source=data_source,
                name=req.get("name", ""),
                description=req.get("description", ""),
                db_table=req.get("db_table", ""),
                db_create_query=req.get("db_create_query", ""),
            )
            models.db.session.commit()
        except IntegrityError as exc:
            abort(400, message=str(exc))

        self.record_event(
            {
                "action": "create",
                "object_id": stream.id,
                "object_type": "stream",
            }
        )

        return stream.to_dict()
