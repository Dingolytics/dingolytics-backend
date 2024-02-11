from pydantic import BaseSettings
from typing import Any, List, Tuple
from redash.defaults import DynamicSettings as BaseDynamicSettings


class ClickHouseSettings(BaseSettings):
    CLICKHOUSE_DB: str = "default"
    CLICKHOUSE_URL: str = "http://clickhouse:8123"
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""


class DynamicSettings(BaseDynamicSettings):
    def __init__(self) -> None:
        super().__init__()
        self.clickhouse_settings = ClickHouseSettings()

    def setup_default_org(self, name: str) -> Tuple[Any, List[Any]]:
        default_org, default_groups = super().setup_default_org(name)
        self.setup_default_data_source(default_org)
        return default_org, default_groups

    def setup_default_data_source(self, default_org: Any):
        from redash.models import DataSource
        datasource = DataSource.create_with_group(
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
        return datasource
