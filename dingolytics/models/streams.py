from secrets import token_urlsafe
from sqlalchemy import UniqueConstraint
from sqlalchemy_utils.models import generic_repr
from redash.settings import get_settings
from redash.models.base import db, Column, primary_key, key_type
from redash.models.datasources import DataSource
from redash.models.mixins import TimestampMixin


def default_ingest_key(n: int = 16) -> str:
    """Generate a random ingest key."""
    return token_urlsafe(n)


@generic_repr("id", "name", "db_table", "is_enabled", "is_archived")
class Stream(TimestampMixin, db.Model):
    id = primary_key("Stream")
    name = Column(db.String(255))
    description = Column(db.Text, nullable=True)

    data_source_id = Column(
        key_type("DataSource"), db.ForeignKey("data_sources.id")
    )
    data_source = db.relationship(DataSource, backref="streams")

    ingest_key = Column(
        db.String(255), unique=True, default=default_ingest_key
    )

    db_table = Column(db.String(255), index=True)
    db_table_preset = Column(db.String(255), index=True, default="app_events")
    db_table_query = Column(db.Text, nullable=True)

    is_enabled = Column(db.Boolean, default=True, index=True)
    is_archived = Column(db.Boolean, default=False, index=True)

    __tablename__ = "streams"

    __table_args__ = (
        UniqueConstraint(
            "data_source_id", "db_table", name="data_source_table"
        ),
    )

    def __str__(self):
        return "%s | %s" % (self.id, self.db_table)

    @property
    def ingest_url(self) -> str:
        host = get_settings().VECTOR_INGEST_URL
        return "{}/ingest/{}".format(host, self.ingest_key)

    @property
    def ingest_example(self) -> dict:
        curl_example = '\n'.join([
            'curl -X POST -H "Content-Type: application/json" \\',
            f"-d '{INGEST_APP_EVENTS_JSON}' \\\n{self.ingest_url}",
        ])
        return {
            'curl': curl_example
        }

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "ingest_key": self.ingest_key,
            "ingest_url": self.ingest_url,
            "ingest_example": self.ingest_example,
            "data_source_id": self.data_source_id,
            "db_table": self.db_table,
            "db_table_preset": self.db_table_preset,
            "db_table_query": self.db_table_query,
            "is_enabled": self.is_enabled,
            "is_archived": self.is_archived,
        }

    @classmethod
    def get_by_id(cls, _id):
        return cls.query.filter(cls.id == _id).one()


CLICKHOUSE_APP_EVENTS_SQL = """
CREATE TABLE {db_table} (
    timestamp DateTime64(3),
    level String,
    message String,
    platform String,
    application String,
    path String
) ENGINE = MergeTree() ORDER BY (timestamp);
""".strip()

INGEST_APP_EVENTS_JSON = """
{"path": "/", "level": "INFO", "application": "main", "platform": "web"}
""".strip()
