from passlib.apps import custom_app_context as pwd_context
from redash import models
from redash.models import db
from redash.permissions import ACCESS_TYPE_MODIFY
from redash.utils import gen_query_hash, utcnow
from redash.utils.configuration import ConfigurationContainer


class ModelFactory(object):
    def __init__(self, model, **kwargs):
        self.model = model
        self.kwargs = kwargs

    def _get_kwargs(self, override_kwargs):
        kwargs = self.kwargs.copy()
        kwargs.update(override_kwargs)

        for key, arg in kwargs.items():
            if callable(arg):
                kwargs[key] = arg()

        return kwargs

    def create(self, **override_kwargs):
        kwargs = self._get_kwargs(override_kwargs)
        obj = self.model(**kwargs)
        db.session.add(obj)
        db.session.commit()
        return obj


class Sequence(object):
    def __init__(self, string):
        self.sequence = 0
        self.string = string

    def __call__(self):
        self.sequence += 1

        return self.string.format(self.sequence)


user_factory = ModelFactory(
    models.User,
    name="John Doe",
    email=Sequence("test{}@example.com"),
    password_hash=pwd_context.hash("test1234"),
    group_ids=[2],
    org_id=1,
)

org_factory = ModelFactory(
    models.Organization,
    name=Sequence("Org {}"),
    slug=Sequence("org{}.example.com"),
    settings={},
)

group_factory = ModelFactory(
    models.Group,
    name=Sequence("Test {}"),
)

data_source_factory = ModelFactory(
    models.DataSource,
    name=Sequence("Test {}"),
    type="pg",
    options=lambda: ConfigurationContainer.from_json('''
        {
            "dbname": "tests",
            "host": "postgres-tests",
            "user": "postgres"
        }
    '''),
    org_id=1,
)

stream_factory = ModelFactory(
    models.Stream,
    name=Sequence("Test {}"),
    data_source=data_source_factory.create,
    db_table='test_stream',    
)

dashboard_factory = ModelFactory(
    models.Dashboard,
    name="test",
    user=user_factory.create,
    layout="[]",
    is_draft=False,
    org=1,
)

api_key_factory = ModelFactory(models.ApiKey, object=dashboard_factory.create)

query_factory = ModelFactory(
    models.Query,
    name="Query",
    description="",
    query_text="SELECT 1",
    user=user_factory.create,
    is_archived=False,
    is_draft=False,
    schedule={},
    data_source=data_source_factory.create,
    org_id=1,
)

query_with_params_factory = ModelFactory(
    models.Query,
    name="New Query with Params",
    description="",
    query_text="SELECT {{param1}}",
    user=user_factory.create,
    is_archived=False,
    is_draft=False,
    schedule={},
    data_source=data_source_factory.create,
    org_id=1,
)

access_permission_factory = ModelFactory(
    models.AccessPermission,
    object_id=query_factory.create,
    object_type=models.Query.__name__,
    access_type=ACCESS_TYPE_MODIFY,
    grantor=user_factory.create,
    grantee=user_factory.create,
)

alert_factory = ModelFactory(
    models.Alert,
    name=Sequence("Alert {}"),
    query_rel=query_factory.create,
    user=user_factory.create,
    options={},
)

query_result_factory = ModelFactory(
    models.QueryResult,
    data='{"columns":{}, "rows":[]}',
    runtime=1,
    retrieved_at=utcnow,
    query_text="SELECT 1",
    query_hash=gen_query_hash("SELECT 1"),
    data_source=data_source_factory.create,
    org_id=1,
)

visualization_factory = ModelFactory(
    models.Visualization,
    type="CHART",
    query_rel=query_factory.create,
    name="Chart",
    description="",
    options="{}",
)

widget_factory = ModelFactory(
    models.Widget,
    width=1,
    options="{}",
    dashboard=dashboard_factory.create,
    visualization=visualization_factory.create,
)

destination_factory = ModelFactory(
    models.NotificationDestination,
    org_id=1,
    user=user_factory.create,
    name=Sequence("Destination {}"),
    type="slack",
    options=lambda: ConfigurationContainer.from_json('{"url": "https://www.slack.com"}'),
)

alert_subscription_factory = ModelFactory(
    models.AlertSubscription,
    user=user_factory.create,
    destination=destination_factory.create,
    alert=alert_factory.create,
)


def init_database():
    default_org = models.Organization(
        name="Default",
        slug="default",
        settings={}
    )
    admin_group = models.Group(
        name="admin",
        permissions=["admin", "super_admin"],
        org=default_org,
        type=models.Group.BUILTIN_GROUP,
    )
    default_group = models.Group(
        name="default",
        permissions=models.Group.DEFAULT_PERMISSIONS,
        org=default_org,
        type=models.Group.BUILTIN_GROUP,
    )
    db.session.add_all([default_org, admin_group, default_group])
    db.session.commit()
    return default_org, admin_group, default_group


class Factory(object):
    def __init__(self):
        self.org, self.admin_group, self.default_group = init_database()
        self._data_source = None
        self._user = None

    @property
    def user(self):
        if self._user is None:
            self._user = self.create_user()
            # Test setup creates users, they need to be in the db by the time
            # the handler's db transaction starts.
            db.session.commit()
        return self._user

    @property
    def data_source(self):
        if self._data_source is None:
            self._data_source = data_source_factory.create(org=self.org)
            db.session.add(
                models.DataSourceGroup(
                    group=self.default_group,
                    data_source=self._data_source
                )
            )
        return self._data_source

    def create_org(self, **kwargs):
        org = org_factory.create(**kwargs)
        self.create_group(
            name="default",
            permissions=models.Group.DEFAULT_PERMISSIONS,
            org=org,
            type=models.Group.BUILTIN_GROUP,
        )
        self.create_group(
            name="admin",
            permissions=["admin"],
            org=org,
            type=models.Group.BUILTIN_GROUP,
        )
        return org

    def create_user(self, **kwargs):
        args = {"org": self.org, "group_ids": [self.default_group.id]}

        if "org" in kwargs:
            args["group_ids"] = [kwargs["org"].default_group.id]

        args.update(kwargs)
        return user_factory.create(**args)

    def create_admin(self, **kwargs):
        args = {
            "org": self.org,
            "group_ids": [self.admin_group.id, self.default_group.id],
        }

        if "org" in kwargs:
            args["group_ids"] = [
                kwargs["org"].default_group.id,
                kwargs["org"].admin_group.id,
            ]

        args.update(kwargs)
        return user_factory.create(**args)

    def create_group(self, **kwargs):
        args = {"name": "Group", "org": self.org}
        args.update(kwargs)
        return group_factory.create(**args)
        # g = models.Group(**args)
        # return g

    def create_alert(self, **kwargs):
        args = {"user": self.user, "query_rel": self.create_query()}

        args.update(**kwargs)
        return alert_factory.create(**args)

    def create_alert_subscription(self, **kwargs):
        args = {"user": self.user, "alert": self.create_alert()}

        args.update(**kwargs)
        return alert_subscription_factory.create(**args)

    def create_data_source(self, **kwargs):
        group = None
        if "group" in kwargs:
            group = kwargs.pop("group")
        args = {"org": self.org}
        args.update(kwargs)

        if group and "org" not in kwargs:
            args["org"] = group.org

        view_only = args.pop("view_only", False)
        data_source = data_source_factory.create(**args)

        if group:
            db.session.add(
                models.DataSourceGroup(
                    group=group, data_source=data_source, view_only=view_only
                )
            )

        return data_source

    def create_stream(self, **kwargs):
        return stream_factory.create(**kwargs)

    def create_dashboard(self, **kwargs):
        args = {"user": self.user, "org": self.org}
        args.update(kwargs)
        return dashboard_factory.create(**args)

    def create_query(self, **kwargs):
        args = {"user": self.user, "data_source": self.data_source, "org": self.org}
        args.update(kwargs)
        return query_factory.create(**args)

    def create_query_with_params(self, **kwargs):
        args = {"user": self.user, "data_source": self.data_source, "org": self.org}
        args.update(kwargs)
        return query_with_params_factory.create(**args)

    def create_access_permission(self, **kwargs):
        args = {"grantor": self.user}
        args.update(kwargs)
        return access_permission_factory.create(**args)

    def create_query_result(self, **kwargs):
        args = {"data_source": self.data_source}

        args.update(kwargs)

        if "data_source" in args and "org" not in args:
            args["org"] = args["data_source"].org

        return query_result_factory.create(**args)

    def create_visualization(self, **kwargs):
        args = {"query_rel": self.create_query()}
        args.update(kwargs)
        return visualization_factory.create(**args)

    def create_visualization_with_params(self, **kwargs):
        args = {"query_rel": self.create_query_with_params()}
        args.update(kwargs)
        return visualization_factory.create(**args)

    def create_widget(self, **kwargs):
        args = {
            "dashboard": self.create_dashboard(),
            "visualization": self.create_visualization(),
        }
        args.update(kwargs)
        return widget_factory.create(**args)

    def create_api_key(self, **kwargs):
        args = {"org": self.org}
        args.update(kwargs)
        return api_key_factory.create(**args)

    def create_destination(self, **kwargs):
        args = {"org": self.org}
        args.update(kwargs)
        return destination_factory.create(**args)
