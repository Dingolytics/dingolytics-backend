from json import dumps as json_dumps
from secrets import token_urlsafe
from sqlalchemy import UniqueConstraint
from sqlalchemy_utils.models import generic_repr

from dingolytics.presets import default_presets
from redash.settings import get_settings
from redash.models.base import db, Column, primary_key, key_type
from redash.models.datasources import DataSource
from redash.models.mixins import TimestampMixin


def default_ingest_key(n: int = 16) -> str:
    """Generate a random ingest key."""
    return token_urlsafe(n)


def default_ingest_example(
    db_type: str, preset_name: str, ingest_url: str
) -> dict:
    json_example = json_dumps(
        default_presets().get_example(db_type, preset_name),
        # indent=2,
    )
    curl_example = '\n'.join([
        'curl -X POST -H "Content-Type: application/json" \\',
        f"-d '{json_example}' \\\n{ingest_url}",
    ])
    return {
        'curl': curl_example
    }


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
        return default_ingest_example(
            db_type=self.data_source.type,
            preset_name=self.db_table_preset,
            ingest_url=self.ingest_url
        )

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
    def create(
        cls, *, data_source: DataSource, db_table_preset: str, **kwargs
    ) -> 'Stream':
        """
        Create a new stream with a specified preset.

        Keyword arguments:

            * data_source -- the data source to associate with the stream
            * db_table_preset -- the name of the preset to use
            * name -- the name of the stream
            * description -- the description of the stream
            * db_table -- the name of the table in the database
        """
        presets = default_presets()
        db_type = data_source.type
        db_table_query = presets[db_type][db_table_preset]
        stream = cls(
            data_source=data_source,
            db_table_preset=db_table_preset,
            db_table_query=db_table_query,
            **kwargs
        )
        db.session.add(stream)
        return stream

    @classmethod
    def get_by_id(cls, _id):
        return cls.query.filter(cls.id == _id).one()
