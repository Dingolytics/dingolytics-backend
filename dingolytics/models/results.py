import datetime
import logging

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import backref
from sqlalchemy_utils.models import generic_repr

from redash import settings
from redash.models.base import Column, db, key_type, primary_key
from redash.models.datasources import DataSource
from redash.models.mixins import BelongsToOrgMixin
from redash.models.organizations import Organization
from redash.utils import gen_query_hash, json_loads

logger = logging.getLogger(__name__)

DESERIALIZED_DATA_ATTR = "_deserialized_data"


class DBPersistence:
    @property
    def data(self):
        if self._data is None:
            return None

        if not hasattr(self, DESERIALIZED_DATA_ATTR):
            setattr(self, DESERIALIZED_DATA_ATTR, json_loads(self._data))

        return self._deserialized_data

    @data.setter
    def data(self, data):
        if hasattr(self, DESERIALIZED_DATA_ATTR):
            delattr(self, DESERIALIZED_DATA_ATTR)
        self._data = data


QueryResultPersistence = (
    settings.D.QueryResultPersistence or DBPersistence
)


@generic_repr("id", "org_id", "data_source_id", "query_hash", "runtime", "retrieved_at")
class QueryResult(db.Model, QueryResultPersistence, BelongsToOrgMixin):
    id = primary_key("QueryResult")
    org_id = Column(key_type("Organization"), db.ForeignKey("organizations.id"))
    org = db.relationship(Organization)
    data_source_id = Column(key_type("DataSource"), db.ForeignKey("data_sources.id"))
    data_source = db.relationship(DataSource, backref=backref("query_results"))
    query_hash = Column(db.String(32), index=True)
    query_text = Column("query", db.Text)
    _data = Column("data", db.Text)
    runtime = Column(postgresql.DOUBLE_PRECISION)
    retrieved_at = Column(db.DateTime(True))

    __tablename__ = "query_results"

    def __str__(self):
        return "%d | %s | %s" % (self.id, self.query_hash, self.retrieved_at)

    def to_dict(self):
        return {
            "id": self.id,
            "query_hash": self.query_hash,
            "query": self.query_text,
            "data": self.data,
            "data_source_id": self.data_source_id,
            "runtime": self.runtime,
            "retrieved_at": self.retrieved_at,
        }

    @classmethod
    def unused(cls, days=7):
        from dingolytics.models.queries import Query
        age_threshold = datetime.datetime.now() - datetime.timedelta(days=days)
        return (
            cls.query.filter(
                Query.id.is_(None), cls.retrieved_at < age_threshold
            ).outerjoin(Query)
        )

    @classmethod
    def get_latest(cls, data_source, query, max_age=0):
        query_hash = gen_query_hash(query)

        if max_age == -1:
            query = cls.query.filter(
                cls.query_hash == query_hash, cls.data_source == data_source
            )
        else:
            query = cls.query.filter(
                cls.query_hash == query_hash,
                cls.data_source == data_source,
                (
                    db.func.timezone("utc", cls.retrieved_at)
                    + datetime.timedelta(seconds=max_age)
                    >= db.func.timezone("utc", db.func.now())
                ),
            )

        return query.order_by(cls.retrieved_at.desc()).first()

    @classmethod
    def store_result(
        cls, org, data_source, query_hash, query, data, run_time, retrieved_at
    ):
        query_result = cls(
            org_id=org,
            query_hash=query_hash,
            query_text=query,
            runtime=run_time,
            data_source=data_source,
            retrieved_at=retrieved_at,
            data=data,
        )

        db.session.add(query_result)
        logging.info("Inserted query (%s) data; id=%s", query_hash, query_result.id)

        return query_result

    @property
    def groups(self):
        return self.data_source.groups
