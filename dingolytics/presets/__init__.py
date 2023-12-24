from functools import lru_cache
from pathlib import Path
from re import sub as re_sub

DEFAULT_PRESETS_PATH = Path(__file__).parent.absolute()


@lru_cache
def default_presets() -> "PresetLoader":
    loader = PresetLoader(base_path=DEFAULT_PRESETS_PATH)
    loader.load_all()
    return loader


class PresetLoader:
    """
    A class responsible for loading (SQL) presets from a given base path.

    Attributes:
        base_path (str): The base path where the SQL presets are located.

    Methods:
        get_item(group: str, name: str) -> str:
            Retrieves the preset with the specified group and name.

        load_all() -> None:
            Loads all presets from the base path and its subdirectories.

        load_dir(path: Path) -> None:
            Loads presets from a specific directory.

    Examples:

        >>> presets = PresetLoader(base_path=".").load_all()
        >>> presets.load_all()
        >>> presets["clickhouse"]["app_events"]
    """
    def __init__(self, base_path: str) -> None:
        self.base_path = Path(base_path)
        self._presets = {}

    def __getitem__(self, key):
        return self._presets[key]

    def __iter__(self):
        return iter(self._presets)

    def __len__(self):
        return len(self._presets)

    # def groups(self) -> list[str]:
    #     return list(self._presets.keys())

    # def get_group(self, group: str) -> dict:
    #     return self._presets[group]

    # def get_item(self, group: str, name: str) -> str:
    #     return self._presets[group][name]

    def load_all(self) -> None:
        for item in self.base_path.iterdir():
            if item.is_dir():
                self.load_dir(item)

    def load_dir(self, path: Path) -> None:
        for item in path.glob("*.sql"):
            presets = self._presets.setdefault(path.name, {})
            self._load(path=item, presets=presets)

    def _load(self, path: Path, presets: dict) -> None:
        assert path.is_file()
        with open(path, "r") as fp:
            text = fp.read()
            text = re_sub(r"\s+", " ", text.strip())
            presets[path.stem] = text
