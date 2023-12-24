import logging
from sqlalchemy import event
from dingolytics.models.streams import Stream, STREAM_SCHEMAS
from dingolytics.ingest import update_vector_config
from dingolytics.presets import default_presets

logger = logging.getLogger(__name__)


@event.listens_for(Stream, "after_insert")
def after_insert_stream(mapper, connection, target) -> None:
    data_source = target.data_source
    if data_source.type not in STREAM_SCHEMAS:
        return
    create_table_for_stream(target)
    update_vector_config([target], clean=False)


def create_table_for_stream(stream: Stream) -> None:
    # TODO: Better way to import enqueue_query (circular dependency)
    from redash.tasks.queries import enqueue_query
    data_source = stream.data_source
    db_table = stream.db_table
    db_table_preset = stream.db_table_preset
    presets = default_presets()
    try:
        sql = presets[data_source.type][db_table_preset]
    except KeyError as exc:
        logger.exception(exc)
        return
    sql = sql.format(db_table=db_table)
    enqueue_query(sql, data_source, None)
