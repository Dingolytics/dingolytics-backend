from pydantic import BaseSettings
from typing import Any, List, Tuple
from redash.defaults import DynamicSettings as BaseDynamicSettings


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
            }
        )

    def setup_default_streams(self, data_source: Any) -> None:
        from dingolytics.models.streams import Stream
        return Stream.create(
            data_source=data_source,
            db_table_preset="_internal_vector_logs",
            **self.clickhouse_settings.CLICKHOUSE_VECTOR_LOGS,
        )
