from collections import defaultdict
from typing import Any, List, Tuple


class DynamicSettings:
    # Since you can define custom primary key types using `database_key_definitions`,
    # you may want to load certain extensions when creating the database. To do so,
    # simply add the name of the extension you'd like to load to this list.
    database_extensions = []

    # This provides the ability to override the way we store QueryResult's
    # data column. Reference implementation: redash.models.DBPersistence
    QueryResultPersistence = None

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
        pass

    def ssh_tunnel_auth(self) -> dict:
        """
        To enable data source connections via SSH tunnels, provide your SSH authentication
        pkey here. Return a string pointing at your **private** key's path (which will be used
        to extract the public key), or a `paramiko.pkey.PKey` instance holding your **public** key.
        """
        return {
            # 'ssh_pkey': 'path_to_private_key', # or instance of `paramiko.pkey.PKey`
            # 'ssh_private_key_password': 'optional_passphrase_of_private_key',
        }

    def database_key_definitions(self, default: dict) -> dict:
        """
        All primary/foreign keys in Redash are of type `db.Integer` by default.
        You may choose to use different column types for primary/foreign keys. To do so, add an entry below for each model you'd like to modify.
        For each model, add a tuple with the database type as the first item, and a dict including any kwargs for the column definition as the second item.
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

    def setup_default_org(name: str) -> Tuple[Any, List[Any]]:
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
        org: Any, group_ids: List[int], name: str, email: str, password: str,
        **kwargs
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
