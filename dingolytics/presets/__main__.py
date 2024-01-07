import json

from . import default_presets

print(
    json.dumps(
        # default_presets()._presets,
        default_presets()._examples,
        indent=2,
        sort_keys=True,
    )
)
