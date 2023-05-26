from tests import BaseTestCase


class TestStreamListResource(BaseTestCase):
    def test_create_stream_for_data_source(self):
        data_source = self.factory.create_data_source()
        admin = self.factory.create_admin()
        data = {
            "data_source_id": data_source.id,
            "name": "Test stream for {}".format(data_source.name),
            "db_table": "default_stream",
        }
        rv = self.make_request(
            "post", "/api/streams", data=data, user=admin,
        )
        self.assertEqual(200, rv.status_code)
        # self.assertIsNone(DataSource.query.get(data_source.id))
