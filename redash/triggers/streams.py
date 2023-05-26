from sqlalchemy import event
from redash.models.streams import Stream, STREAM_SCHEMAS
from redash.ingest import get_vector_config
from redash.ingest import update_vector_config


@event.listens_for(Stream, "after_insert")
def after_insert_stream(mapper, connection, target) -> None:
    data_source = target.data_source
    if data_source.type not in STREAM_SCHEMAS:
        return
    create_table_for_stream(target)
    update_vector_config([target])


def create_table_for_stream(stream: Stream) -> None:
    # TODO: Better way to import enqueue_query (circular dependency)
    from redash.tasks.queries import enqueue_query
    # DEBUG
    # query_text = 'SELECT 1'
    # /DEBUG
    data_source = stream.data_source
    db_table = stream.db_table
    # TODO: Store preset key in the database
    db_table_preset = 'applogs'
    query_text = STREAM_SCHEMAS[data_source.type][db_table_preset]
    query_text = query_text.format(db_table=db_table)
    enqueue_query(query_text, data_source, None)
