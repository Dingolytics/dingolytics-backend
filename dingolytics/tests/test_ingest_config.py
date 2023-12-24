from unittest.mock import patch

from tests import BaseTestCase
from dingolytics.ingest import update_vector_config


class TestIngestVectorConfig(BaseTestCase):
    @patch("redash.tasks.queries.enqueue_query")
    def test_update_vector_config(self, enqueue_query):
        # Before adding streams 1 default sink is created
        vector_config = update_vector_config([], clean=True)
        self.assertEqual(len(vector_config.config["sources"]), 1)
        self.assertEqual(len(vector_config.config["sinks"]), 1)

        # Creating test data source and 2 streams
        data_source = self.factory.create_data_source(
            type="clickhouse", options={
                "dbname": "default",
                "url": "http://localhost:8123",
            }
        )
        streams = [
            self.factory.create_stream(
                db_table="stream_1", data_source=data_source
            ),
            self.factory.create_stream(
                db_table="stream_2", data_source=data_source
            ),
        ]

        # After adding streams 3 sinks are created
        vector_config = update_vector_config(streams, clean=False)
        self.assertEqual(len(vector_config.config["sources"]), 1)
        self.assertEqual(len(vector_config.config["transforms"]), 1)
        self.assertEqual(len(vector_config.config["sinks"]), 3)
