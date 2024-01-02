import json
import time
from unittest import TestCase, skip
# from unittest.mock import Mock, patch

from redash.query_runner import TYPE_INTEGER
from redash.query_runner.clickhouse import ClickHouse, split_multi_query

split_multi_query_samples = [
    # Regular query
    ("SELECT 1", ["SELECT 1"]),
    # Multiple data queries inlined
    ("SELECT 1; SELECT 2;", ["SELECT 1", "SELECT 2"]),
    # Multiline data queries
    (
        """
SELECT 1;
SELECT 2;
""",
        ["SELECT 1", "SELECT 2"],
    ),
    # Commented data queries
    (
        """
-- First query single-line commentary
SELECT 1;

/**
 * Second query multi-line commentary
 */
SELECT 2;

-- Tail single-line commentary

/**
 * Tail multi-line commentary
 */
""",
        [
            "-- First query single-line commentary\nSELECT 1",
            "/**\n * Second query multi-line commentary\n */\nSELECT 2",
        ],
    ),
    # Should skip empty statements
    (
        """
;;;
;
SELECT 1;
""",
        ["SELECT 1"],
    ),
]


class TestClickHouse(TestCase):
    def test_split_multi_query(self):
        for sample in split_multi_query_samples:
            query, expected = sample
            self.assertEqual(split_multi_query(query), expected)

    def test_send_single_query(self):
        query_runner = ClickHouse({
            "url": "http://clickhouse-tests:8123",
            "dbname": "default",
            "user": "default",
            "password": "test1234",
            "timeout": 60
        })
        data, error = query_runner.run_query("SELECT 1", None)
        self.assertIsNone(error)
        self.assertEqual(
            json.loads(data),
            {
                "columns": [
                    {"name": "1", "friendly_name": "1", "type": TYPE_INTEGER},
                ],
                "rows": [
                    {"1": 1},
                ],
            },
        )

    def test_send_multi_query(self):
        query_runner = ClickHouse({
            "url": "http://clickhouse-tests:8123",
            "dbname": "default",
            "user": "default",
            "password": "test1234",
            "timeout": 60
        })

        data, error = query_runner.run_query(
            """
CREATE
TEMPORARY TABLE test AS
SELECT 1;
SELECT * FROM test;
        """,
            None,
        )

        self.assertIsNone(error)
        self.assertEqual(
            json.loads(data),
            {
                "columns": [
                    {"name": "1", "friendly_name": "1", "type": TYPE_INTEGER},
                ],
                "rows": [
                    {"1": 1},
                ],
            },
        )
