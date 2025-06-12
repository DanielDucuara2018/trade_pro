import inspect
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules
from typing import Type

from .base import Base

CURRENT_DIR = Path(__file__).parent
STRATEGIES_PATH = CURRENT_DIR.joinpath("strategies")


def get_module_class(name: str) -> Type[Base]:
    available_names = [mod_name for _, mod_name, _ in iter_modules([STRATEGIES_PATH])]

    if name not in available_names:
        raise Exception(f"Strategy {name} not found")

    module = import_module(f".strategies.{name}", __package__)

    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if inspect.isclass(attr) and issubclass(attr, Base) and attr is not Base:
            return attr

    raise Exception(f"No subclass of Base found in strategy module '{name}'")
