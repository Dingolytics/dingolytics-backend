import logging
import time

from flask import g, has_request_context

from redash import statsd_client
from sqlalchemy.engine import Engine
from sqlalchemy.event import listens_for
from sqlalchemy.orm.util import _ORMJoin
from sqlalchemy.sql.selectable import Alias, Select

metrics_logger = logging.getLogger("metrics")


def _table_name_from_select_element(elt: Select) -> str:
    """Extract the table name from a Select element."""
    # Get the list of tables being selected from
    from_list = elt.get_final_froms()
    # Get the first table in the list
    t = from_list[0]
    # If the table is an Alias, get the underlying table
    if isinstance(t, Alias):
        t = t.element
    # Iterate through join clauses until we find the actual table
    while isinstance(t, _ORMJoin):
        t = t.right
        if isinstance(t, Alias):
            t = t.element
    # Return the name of the table
    return t.name


@listens_for(Engine, "before_execute")
def before_execute(conn, clauseelement, multiparams, params, execution_options):
    conn.info.setdefault("query_start_time", []).append(time.time())


@listens_for(Engine, "after_execute")
def after_execute(conn, clauseelement, multiparams, params,
                  execution_options, result):
    duration = 1000 * (time.time() - conn.info["query_start_time"].pop(-1))
    action = clauseelement.__class__.__name__.lower()

    if action == "select":
        name = "unknown"
        try:
            name = _table_name_from_select_element(clauseelement)
        except Exception:
            logging.exception("Failed finding table name.")
    elif action in ["update", "insert", "delete"]:
        name = clauseelement.table.name
    else:
        # Create / drop tables, SQLAlchemy internal schema queries, etc
        return

    statsd_client.timing("db.{}.{}".format(name, action), duration)

    metrics_logger.debug("table=%s query=%s duration=%.2f", name, action, duration)

    if has_request_context():
        g.setdefault("queries_count", 0)
        g.setdefault("queries_duration", 0)
        g.queries_count += 1
        g.queries_duration += duration

    return result
