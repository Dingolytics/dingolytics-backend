import calendar
import datetime
import logging
import time

import pytz
from sqlalchemy import and_, distinct, func, or_
from sqlalchemy.dialects import postgresql
from sqlalchemy.event import listens_for
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import contains_eager, joinedload
from sqlalchemy_utils.models import generic_repr
from sqlalchemy_utils.types import TSVectorType

from dingolytics.models.results import QueryResult
from redash import redis_connection, utils
from redash.models.base import Column, db, gfk_type, key_type, primary_key
from redash.models.datasources import DataSource, DataSourceGroup
from redash.models.mixins import BelongsToOrgMixin, TimestampMixin
from redash.models.organizations import Organization
from redash.models.parameterized_query import ParameterizedQuery
from redash.models.types import MutableDict, MutableList, json_cast_property
from redash.models.users import User
from redash.query_runner import BaseQueryRunner
from redash.utils import generate_token, sentry

logger = logging.getLogger(__name__)


class ScheduledQueriesExecutions:
    KEY_NAME = "sq:executed_at"

    def __init__(self):
        self.executions = {}

    def refresh(self):
        self.executions = redis_connection.hgetall(self.KEY_NAME)

    def update(self, query_id):
        redis_connection.hset(
            self.KEY_NAME, '', 0, mapping={query_id: time.time()}
        )
        # redis_connection.hmset(self.KEY_NAME, {query_id: time.time()})

    def get(self, query_id):
        timestamp = self.executions.get(str(query_id))
        if timestamp:
            timestamp = utils.dt_from_timestamp(timestamp)

        return timestamp


scheduled_queries_executions = ScheduledQueriesExecutions()


def should_schedule_next(
    previous_iteration, now, interval, time=None, day_of_week=None, failures=0
):
    # if time exists then interval > 23 hours (82800s)
    # if day_of_week exists then interval > 6 days (518400s)
    if time is None:
        ttl = int(interval)
        next_iteration = previous_iteration + datetime.timedelta(seconds=ttl)
    else:
        hour, minute = time.split(":")
        hour, minute = int(hour), int(minute)

        # The following logic is needed for cases like the following:
        # - The query scheduled to run at 23:59.
        # - The scheduler wakes up at 00:01.
        # - Using naive implementation of comparing timestamps, it will skip the execution.
        normalized_previous_iteration = previous_iteration.replace(
            hour=hour, minute=minute
        )

        if normalized_previous_iteration > previous_iteration:
            previous_iteration = normalized_previous_iteration - datetime.timedelta(
                days=1
            )

        days_delay = int(interval) / 60 / 60 / 24

        days_to_add = 0
        if day_of_week is not None:
            days_to_add = (
                list(calendar.day_name).index(day_of_week)
                - normalized_previous_iteration.weekday()
            )

        next_iteration = (
            previous_iteration
            + datetime.timedelta(days=days_delay)
            + datetime.timedelta(days=days_to_add)
        ).replace(hour=hour, minute=minute)
    if failures:
        try:
            next_iteration += datetime.timedelta(minutes=2 ** failures)
        except OverflowError:
            return False
    return now > next_iteration


@gfk_type
@generic_repr(
    "id",
    "name",
    "query_hash",
    "version",
    "user_id",
    "org_id",
    "data_source_id",
    "query_hash",
    "last_modified_by_id",
    "is_archived",
    "is_draft",
    "schedule",
    "schedule_failures",
)
class Query(TimestampMixin, BelongsToOrgMixin, db.Model):
    id = primary_key("Query")
    version = Column(db.Integer, default=1)
    org_id = Column(key_type("Organization"), db.ForeignKey("organizations.id"))
    org = db.relationship(Organization, backref="queries")
    data_source_id = Column(key_type("DataSource"), db.ForeignKey("data_sources.id"), nullable=True)
    data_source = db.relationship(DataSource, backref="queries")
    latest_query_data_id = Column(
        key_type("QueryResult"), db.ForeignKey("query_results.id"), nullable=True
    )
    latest_query_data = db.relationship(QueryResult)
    name = Column(db.String(255))
    description = Column(db.String(4096), nullable=True)
    query_text = Column("query", db.Text)
    query_hash = Column(db.String(32))
    api_key = Column(db.String(40), default=lambda: generate_token(40))
    user_id = Column(key_type("User"), db.ForeignKey("users.id"))
    user = db.relationship(User, foreign_keys=[user_id])
    last_modified_by_id = Column(key_type("User"), db.ForeignKey("users.id"), nullable=True)
    last_modified_by = db.relationship(
        User, backref="modified_queries", foreign_keys=[last_modified_by_id]
    )
    is_archived = Column(db.Boolean, default=False, index=True)
    is_draft = Column(db.Boolean, default=True, index=True)
    schedule = Column(
        MutableDict.as_mutable(postgresql.JSONB),
        server_default="{}", default={}
    )
    interval = json_cast_property(db.Integer, "schedule", "interval", default=0)
    schedule_failures = Column(db.Integer, default=0)
    visualizations = db.relationship("Visualization", cascade="all, delete-orphan")
    options = Column(
        MutableDict.as_mutable(postgresql.JSONB),
        server_default="{}", default={}
    )
    search_vector = Column(
        TSVectorType(
            "id",
            "name",
            "description",
            "query",
            weights={"name": "A", "id": "B", "description": "C", "query": "D"},
        ),
        nullable=True,
    )
    tags = Column(
        "tags", MutableList.as_mutable(postgresql.ARRAY(db.Unicode)), nullable=True
    )

    # query_class = SearchBaseQuery
    __tablename__ = "queries"
    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}

    def __str__(self):
        return str(self.id)

    def archive(self, user=None):
        db.session.add(self)
        self.is_archived = True
        self.schedule = {}

        for vis in self.visualizations:
            for w in vis.widgets:
                db.session.delete(w)

        for a in self.alerts:
            db.session.delete(a)

        # if user:
        #     self.record_changes(user)

    def regenerate_api_key(self):
        self.api_key = generate_token(40)

    @classmethod
    def create(cls, **kwargs):
        from redash.models import Visualization

        query = cls(**kwargs)
        db.session.add(
            Visualization(
                query_rel=query,
                name="Table",
                description="",
                type="TABLE",
                options="{}",
            )
        )
        return query

    @classmethod
    def all_queries(
        cls, group_ids, user_id=None, include_drafts=False, include_archived=False
    ):
        query_ids = (
            db.session.query(distinct(cls.id))
            .join(
                DataSourceGroup,
                Query.data_source_id == DataSourceGroup.data_source_id
            )
            .filter(Query.is_archived.is_(include_archived))
            .filter(DataSourceGroup.group_id.in_(group_ids))
        )
        # print('query_ids:', [x for x in query_ids], flush=True)
        queries = (
            cls.query.options(
                joinedload(Query.user),
                joinedload(Query.latest_query_data).load_only(
                    "runtime", "retrieved_at"
                ),
            )
            .filter(cls.id.in_(query_ids))
            # Adding outer joins to be able to order by relationship
            .outerjoin(User, User.id == Query.user_id)
            .outerjoin(QueryResult, QueryResult.id == Query.latest_query_data_id)
            .options(
                contains_eager(Query.user), contains_eager(Query.latest_query_data)
            )
        )
        # print('queries:', [x for x in queries], flush=True)
        if not include_drafts:
            queries = queries.filter(
                or_(Query.is_draft.is_(False), Query.user_id == user_id)
            )
        return queries

    @classmethod
    def favorites(cls, user, base_query=None):
        from redash.models import Favorite

        if base_query is None:
            base_query = cls.all_queries(user.group_ids, user.id, include_drafts=True)
        return base_query.join(
            (
                Favorite,
                and_(Favorite.object_type == "Query", Favorite.object_id == Query.id),
            )
        ).filter(Favorite.user_id == user.id)

    @classmethod
    def all_tags(cls, user, include_drafts=False):
        queries = cls.all_queries(
            group_ids=user.group_ids,
            user_id=user.id,
            include_drafts=include_drafts
        )
        # print('queries:', [x for x in queries], flush=True)
        tag_column = func.unnest(cls.tags).label("tag")
        usage_count = func.count(1).label("usage_count")
        # queries_ids = [x.id for x in queries.options(load_only("id"))]
        queries_ids = queries.with_entities(Query.id).subquery()
        tags = (
            db.session.query(tag_column, usage_count)
            .group_by(tag_column)
            .filter(Query.id.in_(queries_ids))
            .order_by(usage_count.desc())
        )
        # print('tags:', [x for x in tags], flush=True)
        return tags

    @classmethod
    def by_user(cls, user):
        return cls.all_queries(user.group_ids, user.id).filter(Query.user == user)

    @classmethod
    def by_api_key(cls, api_key):
        return cls.query.filter(cls.api_key == api_key).one()

    @classmethod
    def past_scheduled_queries(cls):
        now = utils.utcnow()
        queries = Query.query.filter(Query.schedule.isnot(None)).order_by(Query.id)
        return [
            query
            for query in queries
            if query.schedule.get("until") is not None
            and pytz.utc.localize(
                datetime.datetime.strptime(query.schedule["until"], "%Y-%m-%d")
            )
            <= now
        ]

    @classmethod
    def outdated_queries(cls):
        queries = (
            Query.query.options(
                joinedload(Query.latest_query_data).load_only("retrieved_at")
            )
            .filter(Query.schedule.isnot(None))
            .order_by(Query.id)
            .all()
        )

        now = utils.utcnow()
        outdated_queries = {}
        scheduled_queries_executions.refresh()

        for query in queries:
            try:
                if query.schedule.get("disabled"):
                    continue

                if query.schedule["until"]:
                    schedule_until = pytz.utc.localize(
                        datetime.datetime.strptime(query.schedule["until"], "%Y-%m-%d")
                    )
                    if schedule_until <= now:
                        continue

                retrieved_at = scheduled_queries_executions.get(query.id) or (
                    query.latest_query_data and query.latest_query_data.retrieved_at
                )

                if should_schedule_next(
                    retrieved_at or now,
                    now,
                    query.schedule["interval"],
                    query.schedule["time"],
                    query.schedule["day_of_week"],
                    query.schedule_failures,
                ):
                    key = "{}:{}".format(query.query_hash, query.data_source_id)
                    outdated_queries[key] = query
            except Exception as e:
                query.schedule["disabled"] = True
                db.session.commit()

                message = (
                    "Could not determine if query %d is outdated due to %s. The schedule for this query has been disabled."
                    % (query.id, repr(e))
                )
                logging.info(message)
                sentry.capture_exception(
                    type(e)(message).with_traceback(e.__traceback__)
                )

        return list(outdated_queries.values())

    @classmethod
    def search(
        cls,
        term,
        group_ids,
        user_id=None,
        include_drafts=False,
        limit=None,
        include_archived=False,
        multi_byte_search=True,
    ):
        all_queries = cls.all_queries(
            group_ids,
            user_id=user_id,
            include_drafts=include_drafts,
            include_archived=include_archived,
        )

        if multi_byte_search:
            # Since tsvector doesn't work well with CJK languages, use `ilike` too
            pattern = "%{}%".format(term)
            return (
                all_queries.filter(
                    or_(cls.name.ilike(pattern), cls.description.ilike(pattern))
                )
                .order_by(Query.id)
                .limit(limit)
            )

        # Sort the result using the weight as defined in the search vector column
        return all_queries.limit(limit)
        # return all_queries.search(term, sort=True).limit(limit)

    @classmethod
    def search_by_user(cls, term, user, limit=None):
        return cls.by_user(user).search(term, sort=True).limit(limit)

    @classmethod
    def recent(cls, group_ids, user_id=None, limit=20):
        from redash.models import DataSourceGroup, Event

        query = (
            cls.query.filter(Event.created_at > (db.func.current_date() - 7))
            .join(Event, Query.id == Event.object_id.cast(db.Integer))
            .join(
                DataSourceGroup, Query.data_source_id == DataSourceGroup.data_source_id
            )
            .filter(
                Event.action.in_(
                    ["edit", "execute", "edit_name", "edit_description", "view_source"]
                ),
                Event.object_id != None,
                Event.object_type == "query",
                DataSourceGroup.group_id.in_(group_ids),
                or_(Query.is_draft == False, Query.user_id == user_id),
                Query.is_archived == False,
            )
            .group_by(Event.object_id, Query.id)
            .order_by(db.desc(db.func.count(0)))
        )

        if user_id:
            query = query.filter(Event.user_id == user_id)

        query = query.limit(limit)

        return query

    @classmethod
    def get_by_id(cls, _id) -> 'Query':
        return cls.query.filter(cls.id == _id).one()

    @classmethod
    def all_groups_for_query_ids(cls, query_ids):
        query = """SELECT group_id, view_only
                   FROM queries
                   JOIN data_source_groups ON queries.data_source_id = data_source_groups.data_source_id
                   WHERE queries.id in :ids"""

        return db.session.execute(query, {"ids": tuple(query_ids)}).fetchall()

    @classmethod
    def update_latest_result(cls, query_result):
        # TODO: Investigate how big an impact this select-before-update makes.
        queries = Query.query.filter(
            Query.query_hash == query_result.query_hash,
            Query.data_source == query_result.data_source,
        )

        for q in queries:
            q.latest_query_data = query_result
            # don't auto-update the updated_at timestamp
            q.skip_updated_at = True
            db.session.add(q)

        query_ids = [q.id for q in queries]
        logging.info(
            "Updated %s queries with result (%s).",
            len(query_ids),
            query_result.query_hash,
        )

        return query_ids

    def fork(self, user):
        from redash.models import Visualization

        forked_list = [
            "org",
            "data_source",
            "latest_query_data",
            "description",
            "query_text",
            "query_hash",
            "options",
            "tags",
        ]
        kwargs = {a: getattr(self, a) for a in forked_list}

        # Query.create will add default TABLE visualization, so use constructor to create bare copy of query
        forked_query = Query(
            name="Copy of (#{}) {}".format(self.id, self.name), user=user, **kwargs
        )

        for v in sorted(self.visualizations, key=lambda v: v.id):
            forked_v = v.copy()
            forked_v["query_rel"] = forked_query
            fv = Visualization(
                **forked_v
            )  # it will magically add it to `forked_query.visualizations`
            db.session.add(fv)

        db.session.add(forked_query)
        return forked_query

    @property
    def runtime(self):
        return self.latest_query_data.runtime

    @property
    def retrieved_at(self):
        return self.latest_query_data.retrieved_at

    @property
    def groups(self):
        if self.data_source is None:
            return {}

        return self.data_source.groups

    @hybrid_property
    def lowercase_name(self):
        "Optional property useful for sorting purposes."
        return self.name.lower()

    @lowercase_name.expression
    def lowercase_name(cls):
        "The SQLAlchemy expression for the property above."
        return func.lower(cls.name)

    @property
    def parameters(self):
        return self.options.get("parameters", [])

    @property
    def parameterized(self):
        return ParameterizedQuery(self.query_text, self.parameters, self.org)

    @property
    def dashboard_api_keys(self):
        query = """SELECT api_keys.api_key
                   FROM api_keys
                   JOIN dashboards ON object_id = dashboards.id
                   JOIN widgets ON dashboards.id = widgets.dashboard_id
                   JOIN visualizations ON widgets.visualization_id = visualizations.id
                   WHERE object_type='dashboards'
                     AND active=true
                     AND visualizations.query_id = :id"""

        api_keys = db.session.execute(query, {"id": self.id}).fetchall()
        return [api_key[0] for api_key in api_keys]

    def update_query_hash(self):
        should_apply_auto_limit = self.options.get("apply_auto_limit", False) if self.options else False
        query_runner = self.data_source.query_runner if self.data_source else BaseQueryRunner({})
        self.query_hash = query_runner.gen_query_hash(self.query_text, should_apply_auto_limit)


@listens_for(Query, "before_insert")
@listens_for(Query, "before_update")
def receive_before_insert_update(mapper, connection, target):
    target.update_query_hash()


@listens_for(Query.user_id, "set")
def query_last_modified_by(target, val, oldval, initiator):
    target.last_modified_by_id = val
