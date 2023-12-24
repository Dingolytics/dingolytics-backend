from functools import lru_cache
from pathlib import Path

BASE_PATH = Path(__file__).parent.absolute()


@lru_cache
def default_loader() -> "Loader":
    loader = Loader(base_path=BASE_PATH)
    loader.load_all()
    return loader


class Loader:
    def __init__(self, base_path: str) -> None:
        self.base_path = Path(base_path)

    def load_all(self):
        pass
