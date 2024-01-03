import logging
import re
from typing import Any, Optional, Tuple
from urllib.parse import urlparse, ParseResult as URL
from uuid import uuid4

from clickhouse_connect import get_client as clickhouse_client
from clickhouse_connect.datatypes.base import ClickHouseType
from clickhouse_connect.driver.client import QueryResult

from redash.query_runner import (
    BaseSQLQueryRunner,
    register,
    split_sql_statements,
    TYPE_STRING,
    TYPE_INTEGER,
    TYPE_FLOAT,
    TYPE_DATETIME,
    TYPE_DATE,
)
from redash.utils import json_dumps, json_loads

logger = logging.getLogger(__name__)


def split_multi_query(query):
    return [st for st in split_sql_statements(query) if st != ""]


class ClickHouse(BaseSQLQueryRunner):
    noop_query = "SELECT 1"

    @classmethod
    def configuration_schema(cls):
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "default": "http://127.0.0.1:8123"},
                "user": {"type": "string", "default": "default"},
                "password": {"type": "string"},
                "dbname": {"type": "string", "title": "Database Name"},
                "timeout": {
                    "type": "number",
                    "title": "Request Timeout",
                    "default": 30,
                },
                "verify": {
                    "type": "boolean",
                    "title": "Verify SSL certificate",
                    "default": True,
                },
            },
            "order": ["url", "user", "password", "dbname"],
            "required": ["dbname"],
            "extra_options": ["timeout", "verify"],
            "secret": ["password"],
        }

    @classmethod
    def type(cls):
        return "clickhouse"

    @property
    def _url(self) -> URL:
        return urlparse(self.configuration["url"])

    @_url.setter
    def _url(self, url: URL):
        self.configuration["url"] = url.geturl()

    @property
    def host(self) -> str:
        return self._url.hostname

    @host.setter
    def host(self, host: str):
        self._url = self._url._replace(netloc=f"{host}:{self._url.port}")

    @property
    def port(self):
        return self._url.port

    @port.setter
    def port(self, port):
        self._url = self._url._replace(netloc=f"{self._url.hostname}:{port}")

    def run_query(
        self, query: str, user: Any
    ) -> Tuple[Optional[str], Optional[str]]:
        queries = split_multi_query(query)

        if not queries:
            data = None
            error = "Query is empty"
            return data, error

        try:
            # If just one query was given no session is needed.
            if len(queries) == 1:
                results = self._clickhouse_query(queries[0])
            else:
                # If more than one query was given, a session is needed.
                # Parameter 'session_check' must be False for the
                # first query.
                session_id = "redash_{}".format(uuid4().hex)
                results = self._clickhouse_query(
                    queries[0], session_id, session_check=False
                )
                for query in queries[1:]:
                    results = self._clickhouse_query(
                        query, session_id, session_check=True
                    )
            data = json_dumps(results)
            error = None
        except Exception as exc:
            data = None
            error = str(exc)
            logging.exception(exc)

        return data, error

    def _get_tables(self, schema):
        system_databases = ', '.join([f"'{db}'" for db in (
            "system",
            "information_schema",
            "INFORMATION_SCHEMA",
        )])
        query = (
            "SELECT database, table, name FROM system.columns"
            f" WHERE database NOT IN ({system_databases})"
        )
        results, error = self.run_query(query, None)
        if error is not None:
            self._handle_run_query_error(error)
        results = json_loads(results)
        for row in results["rows"]:
            table_name = "{}.{}".format(row["database"], row["table"])
            if table_name not in schema:
                schema[table_name] = {"name": table_name, "columns": []}
            schema[table_name]["columns"].append(row["name"])
        return list(schema.values())

    def _send_query(
        self, data, session_id=None, session_check=None
    ) -> QueryResult:
        client = clickhouse_client(
            dsn=self.configuration.get("url", "http://127.0.0.1:8123"),
            username=self.configuration.get("user", "default"),
            password=self.configuration.get("password", ""),
        )
        settings = {
            "session_timeout": self.configuration.get("timeout", 30),
            # "allow_experimental_object_type": 1,
        }
        if session_id:
            settings["session_id"] = session_id
            if session_check:
                settings["session_check"] = session_check
        result = client.query(query=data, settings=settings)
        return result

    @staticmethod
    def _define_column_type(column: ClickHouseType) -> str:
        col = column.name.lower()
        nullable_search = re.search(r"^nullable\((.*)\)$", col)
        if nullable_search is not None:
            col = nullable_search.group(1)
        if col.startswith("int") or col.startswith("uint"):
            return TYPE_INTEGER
        elif col.startswith("float"):
            return TYPE_FLOAT
        elif col == "datetime":
            return TYPE_DATETIME
        elif col == "date":
            return TYPE_DATE
        else:
            return TYPE_STRING

    def _clickhouse_query(
        self, query, session_id=None, session_check=None
    ) -> dict:
        logger.debug("Clickhouse is about to execute query: %s", query)

        result = self._send_query(query, session_id, session_check)

        # Treat Int64 / UInt64 specially, as database converts value
        # to string if its type equals one of these types.
        # NOTE: (Check if this is still in effect for newer versions).
        # types_int64 = (
        #     "Int64",
        #     "UInt64",
        #     "Nullable(Int64)",
        #     "Nullable(UInt64)",
        # )
        columns = []
        # columns_int64 = []
        # columns_totals = {}

        for column_name, column_type in zip(
            result.column_names, result.column_types
        ):
            column_type = self._define_column_type(column_type)
            # if column_type in types_int64:
            #     columns_int64.append(column_name)
            # else:
            #     columns_totals[column_name] = (
            #         "Total" if column_type == TYPE_STRING else None
            #     )
            columns.append({
                "name": column_name,
                "friendly_name": column_name,
                "type": column_type
            })

        # Official Python client returns rows as a list of tuples,
        # but we need a list of dictionaries, and "FORMAT JSON" is ignored,
        # so we manually convert the result.
        # https://clickhouse.com/docs/en/integrations/python
        rows = [
            dict(zip(result.column_names, row)) for row in result.result_rows
        ]

        # TODO: Check how to handle query containing "WITH TOTALS".

        # rows = result.get("data", [])
        # for row in rows:
        #     for column in columns_int64:
        #         try:
        #             row[column] = int(row[column])
        #         except TypeError:
        #             row[column] = None

        # if "totals" in result:
        #     totals = result["totals"]
        #     for column, value in columns_totals.items():
        #         totals[column] = value
        #     rows.append(totals)

        return {"columns": columns, "rows": rows}

register(ClickHouse)
