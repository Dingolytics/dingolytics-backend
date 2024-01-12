import logging
from string import Template
from sqlalchemy import event
from dingolytics.models.streams import Stream
from dingolytics.ingest import sync_vector_config_to_streams
from dingolytics.presets import default_presets

logger = logging.getLogger(__name__)


@event.listens_for(Stream, "after_insert")
def after_insert_stream(mapper, connection, target: Stream) -> None:
    if not target.db_table_query:
        data_source = target.data_source
        db_table_preset = target.db_table_preset
        presets = default_presets()
        try:
            db_presets = presets[data_source.type]
            target.db_table_query = db_presets[db_table_preset]
        except KeyError as exc:
            logger.exception(exc)
            return
    if target.db_table_query:
        create_table_for_stream(target)
        sync_vector_config_to_streams()


def create_table_for_stream(target: Stream) -> None:
    data_source = target.data_source
    db_table = target.db_table
    sql = Template(target.db_table_query).substitute(db_table=db_table)
    query_runner = data_source.query_runner
    data, error = query_runner.run_query(sql, None)
    logger.info(
        "Created table for stream %s: %s data=%s error=%s",
        target.id, db_table, data, error
    )
