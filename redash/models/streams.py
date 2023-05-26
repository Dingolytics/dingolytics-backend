from sqlalchemy_utils.models import generic_repr
from .base import db, Column, primary_key, key_type
from .datasources import DataSource
from .mixins import TimestampMixin


@generic_repr("id", "name", "db_table", "is_enabled", "is_archived")
class Stream(TimestampMixin, db.Model):
    id = primary_key("Stream")
    name = Column(db.String(255))
    description = Column(db.Text, nullable=True)

    data_source_id = Column(
        key_type("DataSource"), db.ForeignKey("data_sources.id")
    )
    data_source = db.relationship(DataSource, backref="streams")

    db_table = Column(db.String(255), unique=True)
    db_create_query = Column(db.Text, nullable=True)

    is_enabled = Column(db.Boolean, default=True, index=True)
    is_archived = Column(db.Boolean, default=False, index=True)

    __tablename__ = "streams"

    def __str__(self):
        return "%s | %s" % (self.id, self.db_table)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "data_source_id": self.data_source_id,
            "db_table": self.db_table,
            "db_create_query": self.db_create_query,
            "is_enabled": self.is_enabled,
            "is_archived": self.is_archived,
        }


STREAM_SCHEMAS = {
    "clickhouse": {
        "rawlogs": """
        """,

        "applogs": """
            CREATE TABLE {db_table} (
                timestamp DateTime64(3),
                level String,
                message String,
                platform String,
                application String,
                path String
            ) ENGINE = MergeTree() ORDER BY (timestamp);
        """,

        "weblogs": """
        """,

        "events": """
        """,

        "metrics": """
        """
    }
}
