from collections import defaultdict
from enum import IntEnum
from typing import Any, List, Tuple

from huey import Huey, PriorityRedisExpireHuey
from pydantic import BaseSettings

__all__ = [
    "DynamicSettings",
    "workers",
]


class ClickHouseSettings(BaseSettings):
    CLICKHOUSE_DB: str = "default"
    CLICKHOUSE_URL: str = "http://clickhouse:8123"
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    CLICKHOUSE_VECTOR_LOGS: dict = {
        "name": "Internal Vector logs",
        "db_table": "vector_logs",
        "description": "Internal logs from Vector ingested into ClickHouse",
    }

    class Config:
        env_file = ".env"


class BaseDynamicSettings:
    # PostgreSQL extensions to use for the main database
    database_extensions: list[str]

    # Reference implementation: redash.models.DBPersistence
    QueryResultPersistence: Any = None

    def query_time_limit(self, is_scheduled: bool, user_id: int, org_id: int):
        """Replace this method with your own implementation in
        case you want to limit the time limit on certain
        queries or users.
        """
        from redash import settings

        if is_scheduled:
            return settings.S.SCHEDULED_QUERY_TIME_LIMIT
        else:
            return settings.S.ADHOC_QUERY_TIME_LIMIT

    def periodic_jobs(self) -> list:
        """Schedule any custom periodic jobs here. For example:

        from time import timedelta
        from somewhere import some_job, some_other_job

        return [
            {"func": some_job, "interval": timedelta(hours=1)},
            {"func": some_other_job, "interval": timedelta(days=1)}
        ]
        """
        return []

    def ssh_tunnel_auth(self) -> dict:
        """
        To enable data source connections via SSH tunnels, provide your SSH
        authentication pkey here. Return a string pointing at your **private**
        key's path (which will be used to extract the public key), or a
        `paramiko.pkey.PKey` instance holding your **public** key.
        """
        return {
            # 'ssh_pkey': 'path_to_private_key', # or instance of `paramiko.pkey.PKey`
            # 'ssh_private_key_password': 'optional_passphrase_of_private_key',
        }

    def database_key_definitions(self, default: dict) -> dict:
        """
        All primary/foreign keys in Redash are of type `db.Integer` by default.
        You may choose to use different column types for primary/foreign keys.
        To do so, add an entry below for each model you'd like to modify.
        For each model, add a tuple with the database type as the first item,
        and a dict including any kwargs for the column definition as the
        second item.
        """
        definitions = defaultdict(lambda: default)
        definitions.update(
            {
                # "DataSource": (db.String(255), {
                #    "default": generate_key
                # })
            }
        )
        return definitions

    def setup_default_org(self, name: str) -> Tuple[Any, List[Any]]:
        """
        Setup the default organization and groups.

        :param name: The name of the organization.

        :return: A tuple containing the organization and a list of groups.
        """
        from redash.models import Group, Organization, db

        default_org = Organization(name=name, slug="default", settings={})
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
        db.session.commit()
        return default_org, [admin_group, default_group]

    def setup_default_user(
        self, *, org: Any, group_ids: List[int], name: str, email: str, password: str, **kwargs
    ) -> Any:
        """Setup the default user."""
        from redash.models import User, db

        user = User(org=org, group_ids=group_ids, name=name, email=email)
        user.hash_password(password)
        db.session.add(user)
        db.session.commit()
        # Signup to newsletter if needed
        # if form.newsletter.data or form.security_notifications:
        #     subscribe.delay(form.data)
        return user


class DynamicSettings(BaseDynamicSettings):
    def __init__(self) -> None:
        super().__init__()
        self.clickhouse_settings = ClickHouseSettings()

    def setup_default_org(self, name: str) -> Tuple[Any, List[Any]]:
        default_org, default_groups = super().setup_default_org(name)
        data_source = self.setup_default_data_source(default_org)
        self.setup_default_streams(data_source)
        return default_org, default_groups

    def setup_default_data_source(self, default_org: Any) -> None:
        from redash.models import DataSource

        return DataSource.create_with_group(
            org=default_org,
            name="Default ClickHouse",
            type="clickhouse",
            options={
                "url": self.clickhouse_settings.CLICKHOUSE_URL,
                "dbname": self.clickhouse_settings.CLICKHOUSE_DB,
                "user": self.clickhouse_settings.CLICKHOUSE_USER,
                "password": self.clickhouse_settings.CLICKHOUSE_PASSWORD,
            },
        )

    def setup_default_streams(self, data_source: Any) -> None:
        from dingolytics.models.streams import Stream

        return Stream.create(
            data_source=data_source,
            db_table_preset="_internal_vector_logs",
            **self.clickhouse_settings.CLICKHOUSE_VECTOR_LOGS,
        )


class HueySettings(BaseSettings):
    HUEY_NAME: str = "default"
    HUEY_URL: str = "redis://keydb:6379/0"
    HUEY_EXPIRE_TIME: int = 86400

    class Config:
        env_file = ".env"

    def get_worker_config(self, **overrides) -> dict[str, Any]:
        config = {k.lower().removeprefix("huey_"): v for k, v in self.dict().items()}
        config.update(overrides)
        return config


class TaskPriority(IntEnum):
    low = 0
    normal = 25
    high = 50
    top = 100


class Workers:
    def __init__(self, settings: HueySettings) -> None:
        self._default = PriorityRedisExpireHuey(**settings.get_worker_config(name="default"))
        # self._adhoc = PriorityRedisExpireHuey(**settings.get_worker_config(name="adhoc"))
        self._periodic = PriorityRedisExpireHuey(**settings.get_worker_config(name="periodic"))

    @property
    def default(self) -> Huey:
        return self._default

    # @property
    # def adhoc(self) -> Huey:
    #     return self._adhoc

    @property
    def periodic(self) -> Huey:
        return self._periodic

workers = Workers(HueySettings())
