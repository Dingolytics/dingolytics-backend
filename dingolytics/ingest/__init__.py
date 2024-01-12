from .vector import VectorConfig
from .vector import get_vector_config
from .vector import update_vector_config

__all__ = [
    'VectorConfig',
    'get_vector_config',
    'update_vector_config',
    'sync_vector_config_to_streams'
]


def sync_vector_config_to_streams() -> None:
    """Sync Vector ingest config to all enabled streams."""
    from redash import models

    streams = models.Stream.query.join(models.DataSource).filter(
        models.DataSource.type.in_(["clickhouse"]),
        models.Stream.is_enabled.is_(True),
        models.Stream.is_archived.is_(False),
    )

    update_vector_config(streams, clean=True)
