import json
from functools import lru_cache
from pathlib import Path
# from re import sub as re_sub

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
        self._examples = {}

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

    def get_example(self, group: str, name: str) -> dict:
        return self._examples.get(group, {}).get(name, {})

    def load_all(self) -> None:
        for item in self.base_path.iterdir():
            if item.is_dir():
                self.load_dir(item)

    def load_dir(self, path: Path) -> None:
        group = path.name
        for item in path.glob("*.sql"):
            presets = self._presets.setdefault(group, {})
            self._load_sql(path=item, presets=presets)
        for item in path.glob("*.example.json"):
            examples = self._examples.setdefault(group, {})
            self._load_example(path=item, examples=examples)

    def _load_example(self, path: Path, examples: dict) -> None:
        assert path.is_file()
        with open(path, "r") as fp:
            key = path.name.split(".")[0]
            examples[key] = json.load(fp)
        
    def _load_sql(self, path: Path, presets: dict) -> None:
        assert path.is_file()
        text = ''
        with open(path, "r") as fp:
            for line in fp:
                if line.startswith("--"):
                    continue
                if not line.strip():
                    continue
                text += line
        key = path.name.split(".")[0]
        presets[key] = text.strip()
