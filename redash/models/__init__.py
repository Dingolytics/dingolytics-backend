import datetime
import logging
import numbers

from sqlalchemy import UniqueConstraint, and_, func, or_
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, joinedload
from sqlalchemy.orm.exc import NoResultFound  # noqa: F401
from sqlalchemy_utils import generic_relationship
from sqlalchemy_utils.models import generic_repr
from sqlalchemy_utils.types.encrypted.encrypted_type import FernetEngine

# Activate triggers for the models
from dingolytics import triggers  # noqa
from dingolytics.models.queries import Query
from dingolytics.models.results import QueryResult  # noqa
from dingolytics.models.streams import Stream  # noqa
from redash import settings, utils
from redash.destinations import (
    get_configuration_schema_for_destination_type,
    get_destination,
)
from redash.metrics import database  # noqa: F401
from redash.utils import base_url, generate_token, mustache_render
from redash.utils.configuration import ConfigurationContainer

from .base import Column, GFKBase, db, gfk_type, key_type, primary_key
from .datasources import DataSource, DataSourceGroup  # noqa
from .mixins import BelongsToOrgMixin, TimestampMixin
from .organizations import Organization
from .types import EncryptedConfiguration, MutableDict, MutableList
from .users import AccessPermission, AnonymousUser, ApiUser, Group, User  # noqa

logger = logging.getLogger(__name__)


@generic_repr("id", "object_type", "object_id", "user_id", "org_id")
class Favorite(TimestampMixin, db.Model):
    id = primary_key("Favorite")
    org_id = Column(key_type("Organization"), db.ForeignKey("organizations.id"))

    object_type = Column(db.Unicode(255))
    object_id = Column(key_type("Favorite"))
    object = generic_relationship(object_type, object_id)

    user_id = Column(key_type("User"), db.ForeignKey("users.id"))
    user = db.relationship(User, backref="favorites")

    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("object_type", "object_id", "user_id", name="unique_favorite"),
    )

    @classmethod
    def is_favorite(cls, user, object):
        return cls.query.filter(cls.object == object, cls.user_id == user).count() > 0

    @classmethod
    def are_favorites(cls, user, objects):
        objects = list(objects)
        if not objects:
            return []

        object_type = str(objects[0].__class__.__name__)
        return [
            fav.object_id
            for fav in cls.query.filter(
                cls.object_id.in_([o.id for o in objects]),
                cls.object_type == object_type,
                cls.user_id == user,
            )
        ]


OPERATORS = {
    ">": lambda v, t: v > t,
    ">=": lambda v, t: v >= t,
    "<": lambda v, t: v < t,
    "<=": lambda v, t: v <= t,
    "==": lambda v, t: v == t,
    "!=": lambda v, t: v != t,
    # backward compatibility
    "greater than": lambda v, t: v > t,
    "less than": lambda v, t: v < t,
    "equals": lambda v, t: v == t,
}


def next_state(op, value, threshold):
    if isinstance(value, bool):
        # If it's a boolean cast to string and lower case, because upper cased
        # boolean value is Python specific and most likely will be confusing to
        # users.
        value = str(value).lower()
    else:
        try:
            value = float(value)
            value_is_number = True
        except ValueError:
            value_is_number = isinstance(value, numbers.Number)

        if value_is_number:
            try:
                threshold = float(threshold)
            except ValueError:
                return Alert.UNKNOWN_STATE
        else:
            value = str(value)

    if op(value, threshold):
        new_state = Alert.TRIGGERED_STATE
    else:
        new_state = Alert.OK_STATE

    return new_state


@generic_repr(
    "id", "name", "query_id", "user_id", "state", "last_triggered_at", "rearm"
)
class Alert(TimestampMixin, BelongsToOrgMixin, db.Model):
    UNKNOWN_STATE = "unknown"
    OK_STATE = "ok"
    TRIGGERED_STATE = "triggered"

    id = primary_key("Alert")
    name = Column(db.String(255))
    query_id = Column(key_type("Query"), db.ForeignKey("queries.id"))
    query_rel = db.relationship(Query, backref=backref("alerts", cascade="all"))
    user_id = Column(key_type("User"), db.ForeignKey("users.id"))
    user = db.relationship(User, backref="alerts")
    options = Column(
        MutableDict.as_mutable(postgresql.JSONB),
        server_default="{}", default={}
    )
    state = Column(db.String(255), default=UNKNOWN_STATE)
    subscriptions = db.relationship("AlertSubscription", cascade="all, delete-orphan")
    last_triggered_at = Column(db.DateTime(True), nullable=True)
    rearm = Column(db.Integer, nullable=True)

    __tablename__ = "alerts"

    @classmethod
    def all(cls, group_ids):
        return (
            cls.query.options(joinedload(Alert.user), joinedload(Alert.query_rel))
            .join(Query)
            .join(
                DataSourceGroup, DataSourceGroup.data_source_id == Query.data_source_id
            )
            .filter(DataSourceGroup.group_id.in_(group_ids))
        )

    @classmethod
    def get_by_id_and_org(cls, object_id, org):
        return super(Alert, cls).get_by_id_and_org(object_id, org, Query)

    def evaluate(self):
        data = self.query_rel.latest_query_data.data

        if data["rows"] and self.options["column"] in data["rows"][0]:
            op = OPERATORS.get(self.options["op"], lambda v, t: False)

            value = data["rows"][0][self.options["column"]]
            threshold = self.options["value"]

            new_state = next_state(op, value, threshold)
        else:
            new_state = self.UNKNOWN_STATE

        return new_state

    def subscribers(self):
        return User.query.join(AlertSubscription).filter(
            AlertSubscription.alert == self
        )

    def render_template(self, template):
        if template is None:
            return ""

        data = self.query_rel.latest_query_data.data
        host = base_url(self.query_rel.org)

        col_name = self.options["column"]
        if data["rows"] and col_name in data["rows"][0]:
            result_value = data["rows"][0][col_name]
        else:
            result_value = None

        context = {
            "ALERT_NAME": self.name,
            "ALERT_URL": "{host}/alerts/{alert_id}".format(host=host, alert_id=self.id),
            "ALERT_STATUS": self.state.upper(),
            "ALERT_CONDITION": self.options["op"],
            "ALERT_THRESHOLD": self.options["value"],
            "QUERY_NAME": self.query_rel.name,
            "QUERY_URL": "{host}/queries/{query_id}".format(
                host=host, query_id=self.query_rel.id
            ),
            "QUERY_RESULT_VALUE": result_value,
            "QUERY_RESULT_ROWS": data["rows"],
            "QUERY_RESULT_COLS": data["columns"],
        }
        return mustache_render(template, context)

    @property
    def custom_body(self):
        template = self.options.get("custom_body", self.options.get("template"))
        return self.render_template(template)

    @property
    def custom_subject(self):
        template = self.options.get("custom_subject")
        return self.render_template(template)

    @property
    def groups(self):
        return self.query_rel.groups

    @property
    def muted(self):
        return self.options.get("muted", False)


def generate_slug(ctx):
    slug = utils.slugify(ctx.current_parameters["name"])
    tries = 1
    while Dashboard.query.filter(Dashboard.slug == slug).first() is not None:
        slug = utils.slugify(ctx.current_parameters["name"]) + "_" + str(tries)
        tries += 1
    return slug


@gfk_type
@generic_repr(
    "id", "name", "slug", "user_id", "org_id", "version", "is_archived", "is_draft"
)
class Dashboard(TimestampMixin, BelongsToOrgMixin, db.Model):
    id = primary_key("Dashboard")
    version = Column(db.Integer)
    org_id = Column(key_type("Organization"), db.ForeignKey("organizations.id"))
    org = db.relationship(Organization, backref="dashboards")
    slug = Column(db.String(140), index=True, default=generate_slug)
    name = Column(db.String(100))
    user_id = Column(key_type("User"), db.ForeignKey("users.id"))
    user = db.relationship(User)
    # layout is no longer used, but kept so we know how to render old dashboards.
    layout = Column(db.Text)
    dashboard_filters_enabled = Column(db.Boolean, default=False)
    is_archived = Column(db.Boolean, default=False, index=True)
    is_draft = Column(db.Boolean, default=True, index=True)
    widgets = db.relationship("Widget", backref="dashboard", lazy="dynamic")
    tags = Column(
        "tags", MutableList.as_mutable(postgresql.ARRAY(db.Unicode)), nullable=True
    )
    options = Column(
        MutableDict.as_mutable(postgresql.JSON), server_default="{}", default={}
    )

    __tablename__ = "dashboards"
    __mapper_args__ = {"version_id_col": version}

    def __str__(self):
        return "%s=%s" % (self.id, self.name)

    @property
    def name_as_slug(self):
        return utils.slugify(self.name)

    @classmethod
    def all(cls, org, group_ids, user_id):
        query = (
            Dashboard.query.options(
                joinedload(Dashboard.user).load_only(
                    "id", "name", "details", "email"
                )
            ).distinct(cls.lowercase_name, Dashboard.created_at, Dashboard.slug)
            .outerjoin(Widget)
            .outerjoin(Visualization)
            .outerjoin(Query)
            .outerjoin(
                DataSourceGroup, Query.data_source_id == DataSourceGroup.data_source_id
            )
            .filter(
                Dashboard.is_archived == False,
                (
                    DataSourceGroup.group_id.in_(group_ids)
                    | (Dashboard.user_id == user_id)
                ),
                Dashboard.org == org,
            )
        )

        query = query.filter(
            or_(Dashboard.user_id == user_id, Dashboard.is_draft == False)
        )

        return query

    @classmethod
    def search(cls, org, groups_ids, user_id, search_term):
        # TODO: switch to FTS
        return cls.all(org, groups_ids, user_id).filter(
            cls.name.ilike("%{}%".format(search_term))
        )

    @classmethod
    def search_by_user(cls, term, user, limit=None):
        return cls.by_user(user).filter(cls.name.ilike("%{}%".format(term))).limit(limit)

    @classmethod
    def all_tags(cls, org, user):
        dashboards = cls.all(org, user.group_ids, user.id)
        tag_column = func.unnest(cls.tags).label("tag")
        usage_count = func.count(1).label("usage_count")
        # dashboards_ids = [x.id for x in dashboards.options(load_only("id"))]
        dashboards_ids = dashboards.with_entities(Dashboard.id).subquery()
        query = (
            db.session.query(tag_column, usage_count)
            .group_by(tag_column)
            .filter(Dashboard.id.in_(dashboards_ids))
            .order_by(usage_count.desc())
        )
        return query

    @classmethod
    def favorites(cls, user, base_query=None):
        if base_query is None:
            base_query = cls.all(user.org, user.group_ids, user.id)
        return base_query.join(
            (
                Favorite,
                and_(
                    Favorite.object_type == "Dashboard",
                    Favorite.object_id == Dashboard.id,
                ),
            )
        ).filter(Favorite.user_id == user.id)

    @classmethod
    def by_user(cls, user):
        return cls.all(user.org, user.group_ids, user.id).filter(Dashboard.user == user)

    @classmethod
    def get_by_slug_and_org(cls, slug, org):
        return cls.query.filter(cls.slug == slug, cls.org == org).one()

    @hybrid_property
    def lowercase_name(self):
        "Optional property useful for sorting purposes."
        return self.name.lower()

    @lowercase_name.expression
    def lowercase_name(cls):
        "The SQLAlchemy expression for the property above."
        return func.lower(cls.name)


@generic_repr("id", "name", "type", "query_id")
class Visualization(TimestampMixin, BelongsToOrgMixin, db.Model):
    id = primary_key("Visualization")
    type = Column(db.String(100))
    query_id = Column(key_type("Query"), db.ForeignKey("queries.id"))
    # query_rel and not query, because db.Model already has query defined.
    query_rel = db.relationship(Query, back_populates="visualizations")
    name = Column(db.String(255))
    description = Column(db.String(4096), nullable=True)
    options = Column(db.Text)

    __tablename__ = "visualizations"

    def __str__(self):
        return "%s %s" % (self.id, self.type)

    @classmethod
    def get_by_id_and_org(cls, object_id, org):
        return super(Visualization, cls).get_by_id_and_org(object_id, org, Query)

    def copy(self):
        return {
            "type": self.type,
            "name": self.name,
            "description": self.description,
            "options": self.options,
        }


@generic_repr("id", "visualization_id", "dashboard_id")
class Widget(TimestampMixin, BelongsToOrgMixin, db.Model):
    id = primary_key("Widget")
    visualization_id = Column(
        key_type("Visualization"), db.ForeignKey("visualizations.id"), nullable=True
    )
    visualization = db.relationship(
        Visualization, backref=backref("widgets", cascade="delete")
    )
    text = Column(db.Text, nullable=True)
    width = Column(db.Integer)
    options = Column(db.Text)
    dashboard_id = Column(key_type("Dashboard"), db.ForeignKey("dashboards.id"), index=True)

    __tablename__ = "widgets"

    def __str__(self):
        return "%s" % self.id

    @classmethod
    def get_by_id_and_org(cls, object_id, org):
        return super(Widget, cls).get_by_id_and_org(object_id, org, Dashboard)


@generic_repr(
    "id", "object_type", "object_id", "action", "user_id", "org_id", "created_at"
)
class Event(db.Model):
    id = primary_key("Event")
    org_id = Column(key_type("Organization"), db.ForeignKey("organizations.id"))
    org = db.relationship(Organization, back_populates="events")
    user_id = Column(key_type("User"), db.ForeignKey("users.id"), nullable=True)
    user = db.relationship(User, backref="events")
    action = Column(db.String(255))
    object_type = Column(db.String(255))
    object_id = Column(db.String(255), nullable=True)
    additional_properties = Column(
        MutableDict.as_mutable(postgresql.JSONB),
        server_default="{}", default={}
    )
    created_at = Column(db.DateTime(True), default=db.func.now())

    __tablename__ = "events"

    def __str__(self):
        return "%s,%s,%s,%s" % (
            self.user_id,
            self.action,
            self.object_type,
            self.object_id,
        )

    def to_dict(self):
        return {
            "org_id": self.org_id,
            "user_id": self.user_id,
            "action": self.action,
            "object_type": self.object_type,
            "object_id": self.object_id,
            "additional_properties": self.additional_properties,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def record(cls, event):
        org_id = event.pop("org_id")
        user_id = event.pop("user_id", None)
        action = event.pop("action")
        object_type = event.pop("object_type")
        object_id = event.pop("object_id", None)

        created_at = datetime.datetime.utcfromtimestamp(event.pop("timestamp"))

        event = cls(
            org_id=org_id,
            user_id=user_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            additional_properties=event,
            created_at=created_at,
        )
        db.session.add(event)
        return event


@generic_repr("id", "created_by_id", "org_id", "active")
class ApiKey(TimestampMixin, GFKBase, db.Model):
    id = primary_key("ApiKey")
    org_id = Column(key_type("Organization"), db.ForeignKey("organizations.id"))
    org = db.relationship(Organization)
    api_key = Column(db.String(255), index=True, default=lambda: generate_token(40))
    active = Column(db.Boolean, default=True)
    # 'object' provided by GFKBase
    object_id = Column(key_type("ApiKey"))
    created_by_id = Column(key_type("User"), db.ForeignKey("users.id"), nullable=True)
    created_by = db.relationship(User)

    __tablename__ = "api_keys"
    __table_args__ = (
        db.Index("api_keys_object_type_object_id", "object_type", "object_id"),
    )

    @classmethod
    def get_by_api_key(cls, api_key):
        return cls.query.filter(cls.api_key == api_key, cls.active == True).one()

    @classmethod
    def get_by_object(cls, object):
        return cls.query.filter(
            cls.object_type == object.__class__.__tablename__,
            cls.object_id == object.id,
            cls.active == True,
        ).first()

    @classmethod
    def create_for_object(cls, object, user):
        k = cls(org=user.org, object=object, created_by=user)
        db.session.add(k)
        return k


@generic_repr("id", "name", "type", "user_id", "org_id", "created_at")
class NotificationDestination(BelongsToOrgMixin, db.Model):
    id = primary_key("NotificationDestination")
    org_id = Column(key_type("Organization"), db.ForeignKey("organizations.id"))
    org = db.relationship(Organization, backref="notification_destinations")
    user_id = Column(key_type("User"), db.ForeignKey("users.id"))
    user = db.relationship(User, backref="notification_destinations")
    name = Column(db.String(255))
    type = Column(db.String(255))
    options = Column(
        "encrypted_options",
        ConfigurationContainer.as_mutable(
            EncryptedConfiguration(
                db.Text, settings.S.DATASOURCE_SECRET_KEY, FernetEngine
            )
        ),
    )
    created_at = Column(db.DateTime(True), default=db.func.now())

    __tablename__ = "notification_destinations"
    __table_args__ = (
        db.Index(
            "notification_destinations_org_id_name", "org_id", "name", unique=True
        ),
    )

    def __str__(self):
        return str(self.name)

    def to_dict(self, all=False):
        d = {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "icon": self.destination.icon(),
        }

        if all:
            schema = get_configuration_schema_for_destination_type(self.type)
            self.options.set_schema(schema)
            d["options"] = self.options.to_dict(mask_secrets=True)

        return d

    @property
    def destination(self):
        return get_destination(self.type, self.options)

    @classmethod
    def all(cls, org):
        notification_destinations = cls.query.filter(cls.org == org).order_by(
            cls.id.asc()
        )

        return notification_destinations

    def notify(self, alert, query, user, new_state, app, host):
        schema = get_configuration_schema_for_destination_type(self.type)
        self.options.set_schema(schema)
        return self.destination.notify(
            alert, query, user, new_state, app, host, self.options
        )


@generic_repr("id", "user_id", "destination_id", "alert_id")
class AlertSubscription(TimestampMixin, db.Model):
    id = primary_key("AlertSubscription")
    user_id = Column(key_type("User"), db.ForeignKey("users.id"))
    user = db.relationship(User)
    destination_id = Column(
        key_type("NotificationDestination"), db.ForeignKey("notification_destinations.id"), nullable=True
    )
    destination = db.relationship(NotificationDestination)
    alert_id = Column(key_type("Alert"), db.ForeignKey("alerts.id"))
    alert = db.relationship(Alert, back_populates="subscriptions")

    __tablename__ = "alert_subscriptions"
    __table_args__ = (
        db.Index(
            "alert_subscriptions_destination_id_alert_id",
            "destination_id",
            "alert_id",
            unique=True,
        ),
    )

    def to_dict(self):
        d = {"id": self.id, "user": self.user.to_dict(), "alert_id": self.alert_id}

        if self.destination:
            d["destination"] = self.destination.to_dict()

        return d

    @classmethod
    def all(cls, alert_id):
        return AlertSubscription.query.join(User).filter(
            AlertSubscription.alert_id == alert_id
        )

    def notify(self, alert, query, user, new_state, app, host):
        if self.destination:
            return self.destination.notify(alert, query, user, new_state, app, host)
        else:
            # User email subscription, so create an email destination object
            config = {"addresses": self.user.email}
            schema = get_configuration_schema_for_destination_type("email")
            options = ConfigurationContainer(config, schema)
            destination = get_destination("email", options)
            return destination.notify(alert, query, user, new_state, app, host, options)


@generic_repr("id", "trigger", "user_id", "org_id")
class QuerySnippet(TimestampMixin, db.Model, BelongsToOrgMixin):
    id = primary_key("QuerySnippet")
    org_id = Column(key_type("Organization"), db.ForeignKey("organizations.id"))
    org = db.relationship(Organization, backref="query_snippets")
    trigger = Column(db.String(255), unique=True)
    description = Column(db.Text)
    user_id = Column(key_type("User"), db.ForeignKey("users.id"))
    user = db.relationship(User, backref="query_snippets")
    snippet = Column(db.Text)

    __tablename__ = "query_snippets"

    @classmethod
    def all(cls, org):
        return cls.query.filter(cls.org == org)

    def to_dict(self):
        d = {
            "id": self.id,
            "trigger": self.trigger,
            "description": self.description,
            "snippet": self.snippet,
            "user": self.user.to_dict(),
            "updated_at": self.updated_at,
            "created_at": self.created_at,
        }

        return d


def init_db():
    default_org = Organization(name="Default", slug="default", settings={})
    admin_group = Group(
        name="admin",
        permissions=["admin", "super_admin"],
        org=default_org,
        type=Group.BUILTIN_GROUP,
    )
    default_group = Group(
        name="default",
        permissions=Group.DEFAULT_PERMISSIONS,
        org=default_org,
        type=Group.BUILTIN_GROUP,
    )

    db.session.add_all([default_org, admin_group, default_group])
    # XXX remove after fixing User.group_ids
    db.session.commit()
    return default_org, admin_group, default_group
