from redash import models
from redash.query_runner import NotSupported
from dingolytics.defaults import TaskPriority, workers


@workers.default.task(expires=30, priority=TaskPriority.top)
def get_schema_task(data_source_id: int, refresh: bool) -> dict:
    try:
        data_source = models.DataSource.get_by_id(data_source_id)
        schema = data_source.get_schema(refresh)
        return {"schema": schema}
    except NotSupported:
        return {
            "error": {
                "code": 1,
                "message": "Data source type does not support retrieving schema",
            }
        }
    except Exception as e:
        return {"error": {"code": 2, "message": "Error retrieving schema", "details": str(e)}}
