import os
from functools import lru_cache
from pathlib import Path
from typing import Any
from pydantic import BaseModel
from toml.encoder import TomlEncoder
import toml

VECTOR_CONFIG_TEMPLATE = '''
data_dir = "/var/lib/vector"

[api]
enabled = true
'''

VECTOR_HTTP_INPUT = "http_server"
VECTOR_HTTP_ROUTER = "http_router"
VECTOR_HTTP_PATH_KEY = "_path_"
VECTOR_SINK_PREFIX = "sink-"
VECTOR_INTERNAL_INPUT = "vector_internal_logs"
# VECTOR_INTERNAL_REMAP = "vector_internal_remap"


@lru_cache
def get_vector_config() -> "VectorConfig":
    config_path = os.environ.get("VECTOR_CONFIG_PATH") or "vector.toml"
    return VectorConfig(config_path)


def is_internal_stream(stream: Any) -> bool:
    return stream.db_table_preset.startswith("_")


def update_vector_config(
    streams: list, clean: bool = False, router_key: str = VECTOR_HTTP_ROUTER
) -> "VectorConfig":
    vector_config = get_vector_config()
    if clean:
        vector_config.clean()
    else:
        vector_config.load()
    router = VectorRouteTransform(key=router_key)
    for stream in streams:
        # TODO: More flexible stream source configuration.
        # Current implementation only supports ingest via HTTP
        # and internal logs.
        if is_internal_stream(stream):
            sink = vector_config.get_sink_for_internal_logs(
                stream=stream
            )
        else:
            sink = vector_config.get_sink_for_stream_ingest(
                stream=stream, router=router,
            )
        if sink:
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


class VectorInternalSource(VectorSection):
    type: str = "internal_logs"


# class VectorInternalTransform(VectorSection):
#     type: str = "remap"
#     inputs: list = [VECTOR_INTERNAL_INPUT]
#     source: str = ".timestamp = to_unix_timestamp(to_timestamp!(.timestamp))"


class VectorHTTPSource(VectorSection):
    type: str = VECTOR_HTTP_INPUT
    address: str = "0.0.0.0:8180"
    method = "POST"
    path = "/ingest"
    path_key: str = VECTOR_HTTP_PATH_KEY
    strict_path: bool = False
    decoding: dict = {"codec": "json"}


class VectorConsoleSink(VectorSection):
    type: str = "console"
    inputs: list = [VECTOR_HTTP_INPUT, VECTOR_INTERNAL_INPUT]
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
    _path_key: str = VECTOR_HTTP_PATH_KEY

    def add_route(self, key: str, condition: str) -> None:
        self.route[key] = condition


class VectorConfig:
    def __init__(self, config_path: str) -> None:
        self.config_path = Path(config_path)
        self.config = {}
        self.add_defaults()

    def clean(self) -> None:
        self.config = {}
        self.add_defaults()

    def load(self) -> None:
        if self.config_path.exists():
            with open(self.config_path) as f:
                self.config = toml.load(f)

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            toml.dump(self.config, f, encoder=TomlEncoder(preserve=True))

    def add_defaults(self) -> None:
        self.config = toml.loads(VECTOR_CONFIG_TEMPLATE)
        self.add_source(VectorInternalSource(key=VECTOR_INTERNAL_INPUT))
        self.add_source(VectorHTTPSource(key=VECTOR_HTTP_INPUT))
        self.add_sink(VectorConsoleSink(key="console"))
        # self.add_transform(VectorInternalTransform(key=VECTOR_INTERNAL_REMAP))

    def add_section(self, item: VectorSection, group_key: str) -> None:
        group = self.config.setdefault(group_key, {})
        # Attributes with leading underscore are for use in code only,
        # so we exclude them from the configuration serialization.
        parameters = {
            k: v for k, v in item.dict().items()
            if not k.startswith("_")
        }
        key = parameters.pop("key")
        group[key] = parameters

    def add_sink(self, sink: VectorSection) -> None:
        self.add_section(sink, "sinks")

    def add_source(self, source: VectorSection) -> None:
        self.add_section(source, "sources")

    def add_transform(self, transform: VectorSection) -> None:
        self.add_section(transform, "transforms")

    def get_sink_for_stream_ingest(
        self, stream: Any, router: VectorRouteTransform,
        prefix: str = VECTOR_SINK_PREFIX,
    ) -> VectorSection:
        """
        Create a sink configuration for a stream ingest.

        The sink will be connected to the HTTP source and the ClickHouse
        database, and the router will route the incoming data to the sink.
        """
        route_key = stream.db_table.replace("_", "-").replace(".", "-")
        path_match = f'.{router._path_key} == "/ingest/{stream.ingest_key}"'
        router.add_route(route_key, path_match)
        options = stream.data_source.options.to_dict()
        return VectorClickHouseSink(
            key=f"{prefix}{route_key}",
            inputs=[f"{router.key}.{route_key}"],
            table=stream.db_table,
            auth=VectorClickHouseAuth(**options),
            endpoint=options["url"],
            database=options["dbname"],
        )

    def get_sink_for_internal_logs(
        self, stream: Any, prefix: str = VECTOR_SINK_PREFIX
    ) -> VectorSection:
        """
        Create a sink configuration for internal logs.

        The sink will be connected to the internal logs source and the
        ClickHouse database for output.
        """
        route_key = stream.db_table.replace("_", "-").replace(".", "-")
        options = stream.data_source.options.to_dict()
        return VectorClickHouseSink(
            key=f"{prefix}{route_key}",
            inputs=[VECTOR_INTERNAL_INPUT],
            table=stream.db_table,
            auth=VectorClickHouseAuth(**options),
            endpoint=options["url"],
            database=options["dbname"],
        )
