from pathlib import Path
from pytest import fixture

BASE_DIR = Path(__file__).parent.absolute()


@fixture
def presets_dir():
    return BASE_DIR / "presets"
