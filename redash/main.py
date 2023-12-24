from dingolytics.ingest import sync_vector_config_to_streams
from redash.app import create_app
from redash.version_check import reset_new_version_status
from redash.models import db


def initialize_app():
    app = create_app()

    with app.app_context():
        db.create_all()
        reset_new_version_status()
        sync_vector_config_to_streams()

    return app


app = initialize_app()
