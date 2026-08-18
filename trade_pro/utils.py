import os
import re
from dataclasses import fields
from pathlib import Path
from typing import Any, Optional, Type, TypeVar

from apischema import deserialize

_config_fields: dict[Type, Optional[Any]] = {}

# Matches calls of the shape os%sget/getenv(<literal>) or os%s[<literal>]
# below, written split up like this so this file doesn't match its own pattern.
_ENV_VAR_PATTERN = re.compile(
    r"os\.(?:environ\.get|getenv)\(\s*[\"']([A-Z0-9_]+)[\"']|os\.environ\[[\"']([A-Z0-9_]+)[\"']\]"
)

PACKAGE_ROOT = Path(__file__).parent


def find_referenced_env_vars(package_root: Path = PACKAGE_ROOT) -> set[str]:
    """Scan every .py file under package_root for os.environ.get(...) /
    os.environ[...] / os.getenv(...) calls with a string-literal name, and
    return the set of environment variable names the codebase actually
    depends on. This is intentionally dynamic (rather than a hardcoded list)
    so a preflight check stays correct as new env vars are added anywhere in
    the package.
    """
    names: set[str] = set()
    for path in package_root.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for match in _ENV_VAR_PATTERN.finditer(text):
            names.add(match.group(1) or match.group(2))
    return names


def check_env_vars(package_root: Path = PACKAGE_ROOT) -> dict[str, bool]:
    """Check whether every environment variable referenced anywhere in the
    codebase is currently set in this process's environment.

    Returns {var_name: is_set}, sorted by name. This does not know which
    vars a *specific* command actually needs (e.g. `fetch` doesn't use the
    Telegram vars at all) — it's a whole-codebase inventory, meant to be
    reviewed/logged before an operation runs so missing configuration is
    visible upfront rather than discovered mid-run.
    """
    return {
        name: os.environ.get(name) is not None
        for name in sorted(find_referenced_env_vars(package_root))
    }


Cls = TypeVar("Cls", bound=Type)


class ConfigurationField:
    def __init__(self, name: str):
        self.name = name

    def __get__(self, instance, owner):
        assert instance is None
        try:
            return getattr(_config_fields[owner], self.name)
        except AttributeError:
            raise RuntimeError("Configuration not loaded") from None
        except KeyError:
            raise RuntimeError("Configuration is not root") from None


def load_configuration(cls: Cls) -> Cls:
    for field_ in fields(cls):
        setattr(cls, field_.name, ConfigurationField(field_.name))
    _config_fields[cls] = None
    return cls


def load_configuration_data(config: dict[str, Any]) -> None:
    for key, _ in _config_fields.items():
        _config_fields[key] = deserialize(key, config)
