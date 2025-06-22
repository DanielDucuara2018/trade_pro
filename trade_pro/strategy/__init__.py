import inspect
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules
from typing import Type

from .base import Base

CURRENT_DIR = Path(__file__).parent
STRATEGIES_PATH = CURRENT_DIR.joinpath("strategies")


def get_module_class(class_name: str) -> Type[Base]:
    for _, mod_name, _ in iter_modules([STRATEGIES_PATH]):
        module = import_module(f".strategies.{mod_name}", __package__)
        attr = getattr(module, class_name, None)

        if (
            attr is not None
            and inspect.isclass(attr)
            and issubclass(attr, Base)
            and attr is not Base
        ):
            return attr

    raise Exception(f"Class '{class_name}' not found in any strategy module.")
