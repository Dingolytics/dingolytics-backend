from typing import Optional
from json import loads as json_loads
from flask import request, Response
from jinja2 import Template
from redash import models
from redash.handlers.base import routes
from redash.security import csp_allows_embeding
from redash.utils import collect_parameters_from_request

DEFAULT_TEMPLATES = {
    "plain.svg": Template(
        '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="{{ width }}" height="{{ height }}" '
            'viewBox="0 0 {{ width }} {{ height }}">'
        '<text x="{{ x }}" y="{{ y }}" fill="{{ color }}" '
            'text-anchor="{{ anchor }}" dominant-baseline="auto" '
            'font-size="{{ size }}" font-family="{{ font }}">'
        '{{ value }}'
        '</text>'
        '</svg>'
    )
}



def template_response(
    template: str, data: dict, error: Optional[str] = None
) -> Optional[Response]:
    # NOTE: We'd want to add custom templates here later.
    if template not in DEFAULT_TEMPLATES:
        return None

    if template.endswith(".svg"):
        try:
            value = data["rows"][0]["value"]
        except (KeyError, IndexError):
            return Response(
                "Query must return a single row with a column named 'value'",
                mimetype="text/plain",
                status=422
            )
        params = request.args.copy()
        params["value"] = value
        params.setdefault("width", 128)
        params.setdefault("height", 32)
        params.setdefault("x", 0)
        params.setdefault("y", 16)
        params.setdefault("anchor", "start")
        params.setdefault("color", "black")
        params.setdefault("size", "1em")
        params.setdefault("font", "sans-serif")
        renderer = DEFAULT_TEMPLATES[template]
        content = renderer.render(**params)
        return Response(content, mimetype="image/svg+xml")

    return None


@routes.route("/ext/widgets/<int:query_id>/<template>", methods=["GET"])
@csp_allows_embeding
def render_widget(query_id: int, template: str):
    query = models.Query.get_by_id(query_id)
    query_runner = query.data_source.query_runner

    parameterized = query.parameterized
    parameterized.apply(
        collect_parameters_from_request(request.args)
    )

    result_str, error = query_runner.run_query(
        # query_runner.annotate_query(parameterized.text, {})
        parameterized.text,
        user=None
    )

    if not error:
        data = json_loads(result_str)
    else:
        data = None

    return template_response(template, data, error) or {
        "data": data,
        "error": error,
    }
