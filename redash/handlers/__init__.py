from flask import jsonify
from flask_login import login_required

from redash.handlers.api import api
from redash.handlers.base import routes
from redash.monitor import get_status
from redash.permissions import require_super_admin
from redash.security import talisman


@routes.route("/ping", methods=["GET"])
@talisman(force_https=False)
def ping():
    return "PONG."


@routes.route("/status.json")
@login_required
@require_super_admin
def status_api():
    status = get_status()
    return jsonify(status)


def init_app(app):
    from redash.handlers import (
        embed,  # noqa: F401
        queries,  # noqa: F401
        static,  # noqa: F401
        authentication,  # noqa: F401
        admin,  # noqa: F401
        setup,  # noqa: F401
        organization,  # noqa: F401
    )

    app.register_blueprint(routes)

    api.init_app(app)
