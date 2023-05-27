import os
from importlib import import_module
from pkgutil import iter_modules

# from trade_pro.strategy.base import Base

CURRENT_FOLDER_PATH = os.path.dirname(os.path.abspath(__file__))
STRATEGIES_PATH = os.path.join(CURRENT_FOLDER_PATH, "strategies")


def get_module(name: str):
    modules = {
        name: import_module(f".strategies.{name}", __package__)
        for _, name, _ in iter_modules([STRATEGIES_PATH])
    }
    try:
        return modules[name]
    except KeyError:
        Exception(f"Strategy {name} not found")
