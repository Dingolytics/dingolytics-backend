import logging
from sqlalchemy import event
from dingolytics.models.streams import Stream
from dingolytics.ingest import update_vector_config
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
        update_vector_config([target], clean=False)


def create_table_for_stream(target: Stream) -> None:
    # TODO: Better way to import enqueue_query (circular dependency)
    from redash.tasks.queries import enqueue_query
    data_source = target.data_source
    db_table = target.db_table
    sql = target.db_table_query.format(db_table=db_table)
    enqueue_query(sql, data_source, None)
