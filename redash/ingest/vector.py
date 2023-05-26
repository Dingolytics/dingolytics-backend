import os
from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel
import toml

VECTOR_CONFIG_TEMPLATE = '''
data_dir = "/var/lib/vector"

[api]
enabled = true
'''

VECTOR_HTTP_INPUT = "http_server"
VECTOR_HTTP_ROUTER = "http_router"
VECTOR_HTTP_PATH_KEY = "_path_"


@lru_cache
def get_vector_config() -> "VectorConfig":
    config_path = os.environ.get("VECTOR_CONFIG_PATH") or "vector.toml"
    return VectorConfig(config_path)


def update_vector_config(
    streams: list, clean: bool = False, sink_prefix: str = "ingest-",
    path_key: str = VECTOR_HTTP_PATH_KEY, router_key: str = VECTOR_HTTP_ROUTER
) -> "VectorConfig":
    vector_config = get_vector_config()
    if not clean:
        vector_config.load()
    router = VectorRouteTransform(key=router_key)
    for stream in streams:
        key = stream.db_table.replace("_", "-").replace(".", "-")
        sink_key = f"{sink_prefix}{key}"
        path_val = f"/{key}"  # TODO: Use random or salted hash
        router.add_route(key, f'.{path_key} == "{path_val}"')
        options = stream.data_source.options.to_dict()
        sink = VectorClickHouseSink(
            key=sink_key,
            inputs=[f"{router_key}.{key}"],
            table=stream.db_table,
            auth=VectorClickHouseAuth(**options),
            endpoint=options["url"],
            database=options["dbname"],
        )
        vector_config.add_sink(sink)
        # print(sink)
        # print(stream)
        # print(stream.data_source)
        # print(stream.data_source.options.to_dict())
    vector_config.add_transform(router)
    vector_config.save()
    return vector_config


class VectorSection(BaseModel):
    key: str


class VectorHTTPSource(VectorSection):
    type: str = VECTOR_HTTP_INPUT
    address: str = "0.0.0.0:8000"
    method = "POST"
    path_key: str = VECTOR_HTTP_PATH_KEY
    decoding: dict = {"codec": "json"}


class VectorConsoleSink(VectorSection):
    type: str = "console"
    inputs: list = [VECTOR_HTTP_INPUT]
    encoding: dict = {"codec": "json"}


class VectorClickHouseAuth(BaseModel):
    strategy: str = "basic"
    user: str = "default"
    password: str = ""


class VectorClickHouseSink(VectorSection):
    database: str
    table: str
    type: str = "clickhouse"
    auth: VectorClickHouseAuth = VectorClickHouseAuth()
    inputs: list = [VECTOR_HTTP_INPUT]
    encoding: dict = {"timestamp_format": "rfc3339"}
    endpoint: str = "http://clickhouse:8123"


class VectorRouteTransform(VectorSection):
    type: str = "route"
    inputs: list = [VECTOR_HTTP_INPUT]
    route: dict = {}

    def add_route(self, key: str, condition: str) -> None:
        self.route[key] = condition


class VectorConfig:
    def __init__(self, config_path: str) -> None:
        self.config = {}
        self.config_path = Path(config_path)
        self.add_defaults()

    def load(self) -> None:
        if self.config_path.exists():
            with open(self.config_path) as f:
                self.config = toml.load(f)

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            toml.dump(self.config, f)

    def add_defaults(self) -> None:
        self.config = toml.loads(VECTOR_CONFIG_TEMPLATE)
        self.add_source(VectorHTTPSource(key=VECTOR_HTTP_INPUT))
        self.add_sink(VectorConsoleSink(key="console"))

    def add_section(self, item: VectorSection, group_key: str) -> None:
        group = self.config.setdefault(group_key, {})
        parameters = item.dict()
        key = parameters.pop("key")
        group[key] = parameters

    def add_sink(self, sink: VectorSection) -> None:
        self.add_section(sink, "sinks")

    def add_source(self, source: VectorSection) -> None:
        self.add_section(source, "sources")

    def add_transform(self, transform: VectorSection) -> None:
        self.add_section(transform, "transforms")
