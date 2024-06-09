from redash.models import db


def usage_data():
    counts_query = """
    SELECT 'users_count' as name, count(0) as value
    FROM users
    WHERE disabled_at is null

    UNION ALL

    SELECT 'queries_count' as name, count(0) as value
    FROM queries
    WHERE is_archived is false

    UNION ALL

    SELECT 'alerts_count' as name, count(0) as value
    FROM alerts

    UNION ALL

    SELECT 'dashboards_count' as name, count(0) as value
    FROM dashboards
    WHERE is_archived is false

    UNION ALL

    SELECT 'widgets_count' as name, count(0) as value
    FROM widgets
    WHERE visualization_id is not null

    UNION ALL

    SELECT 'textbox_count' as name, count(0) as value
    FROM widgets
    WHERE visualization_id is null
    """

    data_sources_query = "SELECT type, count(0) FROM data_sources GROUP by 1"
    visualizations_query = "SELECT type, count(0) FROM visualizations GROUP by 1"
    destinations_query = (
        "SELECT type, count(0) FROM notification_destinations GROUP by 1"
    )

    data = {name: value for (name, value) in db.session.execute(counts_query)}
    data["data_sources"] = {
        name: value for (name, value) in db.session.execute(data_sources_query)
    }
    data["visualization_types"] = {
        name: value for (name, value) in db.session.execute(visualizations_query)
    }
    data["destination_types"] = {
        name: value for (name, value) in db.session.execute(destinations_query)
    }

    return data
