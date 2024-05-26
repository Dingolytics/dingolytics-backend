import datetime
import logging
from contextlib import contextmanager
from unittest import TestCase

from dingolytics.defaults import workers
from redash import limiter, redis_connection
from redash.app import create_app
from redash.models import db
from redash.utils import json_dumps
from tests.factories import Factory, user_factory

# logging.disable(logging.INFO)
logging.getLogger("metrics").setLevel(logging.ERROR)


def authenticate_request(c, user):
    with c.session_transaction() as session:
        session["_user_id"] = user.get_id()


@contextmanager
def authenticated_user(c, user=None):
    if not user:
        user = user_factory.create()
        db.session.commit()
    authenticate_request(c, user)
    yield user


class BaseTestCase(TestCase):
    def setUp(self):
        workers.default.immediate = True
        limiter.enabled = False
        self.app = create_app()
        self.db = db
        self.app.config["TESTING"] = True
        self.app_ctx = self.app.app_context()
        self.app_ctx.push()
        db.session.close()
        db.drop_all()
        db.create_all()
        self.factory = Factory()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.app_ctx.pop()
        redis_connection.flushdb()
        workers.default.immediate = False

    def make_request(
        self,
        method,
        path,
        org=None,
        user=None,
        data=None,
        is_json=True,
        follow_redirects=False,
    ):
        if user is None:
            user = self.factory.user

        if org is None:
            org = self.factory.org

        if org is not False:
            path = "/{}{}".format(org.slug, path)

        if user:
            authenticate_request(self.client, user)

        method_fn = getattr(self.client, method.lower())
        headers = {}

        if data and is_json:
            data = json_dumps(data)

        if is_json:
            content_type = "application/json"
        else:
            content_type = None

        response = method_fn(
            path,
            data=data,
            headers=headers,
            content_type=content_type,
            follow_redirects=follow_redirects,
        )
        return response

    def get_request(self, path, org=None, headers=None):
        if org:
            path = "/{}{}".format(org.slug, path)

        return self.client.get(path, headers=headers)

    def post_request(self, path, data=None, org=None, headers=None):
        if org:
            path = "/{}{}".format(org.slug, path)

        return self.client.post(path, data=data, headers=headers)

    def assertResponseEqual(self, expected, actual):
        for k, v in expected.items():
            if isinstance(v, datetime.datetime) or isinstance(
                actual[k], datetime.datetime
            ):
                continue

            if isinstance(v, list):
                continue

            if isinstance(v, dict):
                self.assertResponseEqual(v, actual[k])
                continue

            self.assertEqual(
                v,
                actual[k],
                "{} not equal (expected: {}, actual: {}).".format(k, v, actual[k]),
            )
