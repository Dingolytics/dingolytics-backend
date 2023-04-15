import functools

from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.query import Query as BaseQuery
from sqlalchemy.orm import object_session
from sqlalchemy.pool import NullPool
from sqlalchemy_searchable import make_searchable, vectorizer, SearchQueryMixin
from sqlalchemy.dialects import postgresql

from redash import settings
from redash.utils import json_dumps


# class RedashSQLAlchemy(SQLAlchemy):
#     def _make_engine(self, *args, **kwargs):
#         # DEBUG:
#         print("RedashSQLAlchemy._make_engine", flush=True)
#         print("args: ", args, flush=True)
#         print("kwargs: ", kwargs, flush=True)
#         # /DEBUG:
#         return super()._make_engine(*args, **kwargs)


def get_engine_options() -> dict:
    """Get engine options for SQLAlchemy."""
    # TODO: Utilize the `SQLALCHEMY_ENGINE_OPTIONS` setting via `app.config`
    engine_options = {"json_serializer": json_dumps}
    if settings.SQLALCHEMY_ENABLE_POOL_PRE_PING:
        engine_options.update(pool_pre_ping=True)
    if settings.SQLALCHEMY_DISABLE_POOL:
        engine_options.update(poolclass=NullPool)
        engine_options.pop("max_overflow", None)
    return engine_options


db = SQLAlchemy(
    engine_options=get_engine_options(),
    session_options={"expire_on_commit": False},
)


# Listen to a few database events to set up functions, trigger updates
# and indexes for the full text search
make_searchable(db.metadata, options={"regconfig": "pg_catalog.simple"})


class SearchBaseQuery(BaseQuery, SearchQueryMixin):
    """
    The SQA query class to use when full text search is wanted.
    """


@vectorizer(db.Integer)
def integer_vectorizer(column):
    return db.func.cast(column, db.Text)


@vectorizer(postgresql.UUID)
def uuid_vectorizer(column):
    return db.func.cast(column, db.Text)


Column = functools.partial(db.Column, nullable=False)

# AccessPermission and Change use a 'generic foreign key' approach to refer to
# either queries or dashboards.
# TODO replace this with association tables.
_gfk_types = {}


def gfk_type(cls):
    _gfk_types[cls.__tablename__] = cls
    return cls


class GFKBase(object):
    """
    Compatibility with 'generic foreign key' approach Django used.
    """

    object_type = Column(db.String(255))
    object_id = Column(db.Integer)

    _object = None

    @property
    def object(self):
        session = object_session(self)
        if self._object or not session:
            return self._object
        else:
            object_class = _gfk_types[self.object_type]
            self._object = (
                session.query(object_class)
                .filter(object_class.id == self.object_id)
                .first()
            )
            return self._object

    @object.setter
    def object(self, value):
        self._object = value
        self.object_type = value.__class__.__tablename__
        self.object_id = value.id


key_definitions = settings.dynamic_settings.database_key_definitions((db.Integer, {}))


def key_type(name):
    return key_definitions[name][0]


def primary_key(name):
    key_type, kwargs = key_definitions[name]
    return Column(key_type, primary_key=True, **kwargs)
