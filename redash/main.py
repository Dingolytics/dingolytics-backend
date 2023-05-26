from .app import create_app
from .ingest import sync_vector_config_to_streams
from .version_check import reset_new_version_status
from .models import db


def initialize_app():
    app = create_app()

    with app.app_context():
        db.create_all()
        reset_new_version_status()
        sync_vector_config_to_streams()

    return app


app = initialize_app()
