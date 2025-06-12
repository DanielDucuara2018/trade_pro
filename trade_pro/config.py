import logging
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path

from trade_pro.utils import load_configuration_data

ROOT = Path(__file__).parents[1]

logger = logging.getLogger(__name__)


@dataclass
class Database:
    database: str
    host: str
    password: str
    port: int
    user: str
    ref_table: str


def bootstrap_configuration(path: str | Path = ROOT.joinpath("trade_pro.ini")) -> None:
    logger.info("Loading configuration from file %s", path)
    config = ConfigParser()
    config.read(path)
    config_dict = {section: dict(config.items(section)) for section in config.sections()}
    load_configuration_data(config_dict)


bootstrap_configuration()
