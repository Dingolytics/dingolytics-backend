import logging

from sqlalchemy_utils.types.encrypted.encrypted_type import FernetEngine
from sqlalchemy_utils.models import generic_repr

from redash import redis_connection, settings
from redash.query_runner import (
    get_configuration_schema_for_query_runner_type,
    get_query_runner,
    with_ssh_tunnel,
)
from redash.utils import json_dumps, json_loads
from redash.utils.configuration import ConfigurationContainer

from .base import db, Column, key_type, primary_key
from .mixins import BelongsToOrgMixin
from .organizations import Organization
from .types import EncryptedConfiguration
from .users import Group

logger = logging.getLogger(__name__)


@generic_repr("id", "name", "type", "org_id", "created_at")
class DataSource(BelongsToOrgMixin, db.Model):
    id = primary_key("DataSource")
    org_id = Column(key_type("Organization"), db.ForeignKey("organizations.id"))
    org = db.relationship(Organization, backref="data_sources")

    name = Column(db.String(255))
    type = Column(db.String(255))
    options = Column(
        "encrypted_options",
        ConfigurationContainer.as_mutable(
            EncryptedConfiguration(
                db.Text, settings.DATASOURCE_SECRET_KEY, FernetEngine
            )
        ),
    )
    queue_name = Column(db.String(255), default="queries")
    scheduled_queue_name = Column(db.String(255), default="scheduled_queries")
    created_at = Column(db.DateTime(True), default=db.func.now())

    data_source_groups = db.relationship(
        "DataSourceGroup", back_populates="data_source", cascade="all"
    )
    __tablename__ = "data_sources"
    __table_args__ = (db.Index("data_sources_org_id_name", "org_id", "name"),)

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def to_dict(self, all=False, with_permissions_for=None):
        d = {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "syntax": self.query_runner.syntax,
            "paused": self.paused,
            "pause_reason": self.pause_reason,
            "supports_auto_limit": self.query_runner.supports_auto_limit
        }

        if all:
            schema = get_configuration_schema_for_query_runner_type(self.type)
            self.options.set_schema(schema)
            d["options"] = self.options.to_dict(mask_secrets=True)
            d["queue_name"] = self.queue_name
            d["scheduled_queue_name"] = self.scheduled_queue_name
            d["groups"] = self.groups

        if with_permissions_for is not None:
            d["view_only"] = (
                db.session.query(DataSourceGroup.view_only)
                .filter(
                    DataSourceGroup.group == with_permissions_for,
                    DataSourceGroup.data_source == self,
                )
                .one()[0]
            )

        return d

    def __str__(self):
        return str(self.name)

    @classmethod
    def create_with_group(cls, *args, **kwargs):
        data_source = cls(*args, **kwargs)
        data_source_group = DataSourceGroup(
            data_source=data_source, group=data_source.org.default_group
        )
        db.session.add_all([data_source, data_source_group])
        return data_source

    @classmethod
    def all(cls, org, group_ids=None):
        data_sources = cls.query.filter(cls.org == org).order_by(cls.id.asc())

        if group_ids:
            data_sources = data_sources.join(DataSourceGroup).filter(
                DataSourceGroup.group_id.in_(group_ids)
            )

        return data_sources.distinct()

    @classmethod
    def get_by_id(cls, _id):
        return cls.query.filter(cls.id == _id).one()

    def delete(self):
        from . import Query, QueryResult  # pylint: disable=C0415
        Query.query.filter(Query.data_source == self).update(
            dict(data_source_id=None, latest_query_data_id=None)
        )
        QueryResult.query.filter(QueryResult.data_source == self).delete()
        res = db.session.delete(self)
        db.session.commit()

        redis_connection.delete(self._schema_key)

        return res

    def get_cached_schema(self):
        cache = redis_connection.get(self._schema_key)
        return json_loads(cache) if cache else None

    def get_schema(self, refresh=False):
        out_schema = None
        if not refresh:
            out_schema = self.get_cached_schema()

        if out_schema is None:
            query_runner = self.query_runner
            schema = query_runner.get_schema(get_stats=refresh)

            try:
                out_schema = self._sort_schema(schema)
            except Exception:
                logging.exception(
                    "Error sorting schema columns for data_source {}".format(self.id)
                )
                out_schema = schema
            finally:
                redis_connection.set(self._schema_key, json_dumps(out_schema))

        return out_schema

    def _sort_schema(self, schema):
        def sort_key(x):
            if isinstance(x, dict):
                return x["name"]
            return x
        return [
            {
                "name": i["name"],
                "columns": sorted(i["columns"], key=sort_key)
            }
            for i in sorted(schema, key=sort_key)
        ]

    @property
    def _schema_key(self):
        return "data_source:schema:{}".format(self.id)

    @property
    def _pause_key(self):
        return "ds:{}:pause".format(self.id)

    @property
    def paused(self):
        return redis_connection.exists(self._pause_key)

    @property
    def pause_reason(self):
        return redis_connection.get(self._pause_key)

    def pause(self, reason=None):
        redis_connection.set(self._pause_key, reason or "")

    def resume(self):
        redis_connection.delete(self._pause_key)

    def add_group(self, group, view_only=False):
        dsg = DataSourceGroup(
            group=group,
            data_source=self,
            view_only=view_only
        )
        db.session.add(dsg)
        return dsg

    def remove_group(self, group):
        DataSourceGroup.query.filter(
            DataSourceGroup.group == group,
            DataSourceGroup.data_source == self,
        ).delete()
        db.session.commit()

    def update_group_permission(self, group, view_only):
        dsg = DataSourceGroup.query.filter(
            DataSourceGroup.group == group,
            DataSourceGroup.data_source == self,
        ).one()
        dsg.view_only = view_only
        db.session.add(dsg)
        return dsg

    @property
    def uses_ssh_tunnel(self):
        return "ssh_tunnel" in self.options

    @property
    def query_runner(self):
        query_runner = get_query_runner(self.type, self.options)
        if self.uses_ssh_tunnel:
            options = self.options.get("ssh_tunnel")
            query_runner = with_ssh_tunnel(query_runner, options)
        return query_runner

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter(cls.name == name).one()

    # XXX Examine call sites to see if a regular SQLA collection
    # would work better
    @property
    def groups(self):
        groups = DataSourceGroup.query.filter(
            DataSourceGroup.data_source == self
        )
        return dict([
            (group.group_id, group.view_only) for group in groups
        ])


@generic_repr("id", "data_source_id", "group_id", "view_only")
class DataSourceGroup(db.Model):
    # XXX Drop id, use datasource/group as PK
    id = primary_key("DataSourceGroup")
    data_source_id = Column(key_type("DataSource"), db.ForeignKey("data_sources.id"))
    data_source = db.relationship(DataSource, back_populates="data_source_groups")
    group_id = Column(key_type("Group"), db.ForeignKey("groups.id"))
    group = db.relationship(Group, back_populates="data_sources")
    view_only = Column(db.Boolean, default=False)

    __tablename__ = "data_source_groups"
