from flask import request
from flask_restful import abort
from sqlalchemy.exc import IntegrityError

from dingolytics.presets import default_presets
from redash import models
from redash.handlers.base import (
    BaseResource,
    get_object_or_404,
    require_fields
)
from redash.permissions import (
    require_access,
    require_admin,
    require_permission,
    view_only,
)


class StreamResource(BaseResource):
    @require_permission("list_data_sources")
    def get(self, stream_id):
        stream = get_object_or_404(models.Stream.get_by_id, stream_id)
        data_source = stream.data_source
        require_access(data_source, self.current_user, view_only)
        self.record_event({
            "action": "view",
            "object_id": stream.id,
            "object_type": "stream",
        })
        return stream.to_dict()


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

        self.record_event({
            "action": "list",
            "object_type": "stream",
        })

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

        # TODO: Cleaner validation code
        db_type = data_source.type
        db_table_preset = req.get("db_table_preset", "app_events")
        presets = default_presets()
        if db_type not in presets:
            abort(400, message=f"Unsupported data source type: {db_type}")
        # TODO: More explicit internal streams handling, e.g. load
        # internal stream presets with a special argument only.
        if db_table_preset.startswith("_"):
            abort(400, message=f"Internal stream preset: {db_table_preset}")
        if db_table_preset not in presets[db_type]:
            abort(400, message=f"Unsupported stream preset: {db_table_preset}")
        db_table_query = presets[db_type][db_table_preset]

        try:
            stream = models.Stream(
                data_source=data_source,
                name=req.get("name", ""),
                description=req.get("description", ""),
                db_table=req.get("db_table", ""),
                db_table_preset=db_table_preset,
                db_table_query=db_table_query,
            )
            models.db.session.commit()
        except IntegrityError as exc:
            abort(400, message=str(exc))

        self.record_event({
            "action": "create",
            "object_id": stream.id,
            "object_type": "stream",
        })

        return stream.to_dict()
