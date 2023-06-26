import logging
import os
from dataclasses import dataclass, field
from typing import Optional

import yaml
from binance import AsyncClient

from trade_pro.rabbitmq.config import Consumer, Publisher
from trade_pro.rabbitmq.consumer import default_queue_factory
from trade_pro.rabbitmq.publisher import default_exchange_factory
from trade_pro.utils import load_configuration, load_configuration_data

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINANCE_API_KEY: Optional[str] = os.environ.get("binance_api_key")
BINANCE_SECRETE_KEY: Optional[str] = os.environ.get("binance_secret_key")
TELEGRAM_BOT_TOKEN: Optional[str] = os.environ.get("telegram_bot_token")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


async def create_binance_client():
    return await AsyncClient.create(BINANCE_API_KEY, BINANCE_SECRETE_KEY)


@dataclass
class Database:
    database: str
    host: str
    password: str
    port: int
    user: str
    ref_table: str


@dataclass
class AMQP:
    consumer: Consumer
    publisher: Publisher
    default_exchange: str = field(default="")
    time_to_reconnect: int = field(default=2)  # in seconds
    message_expiration: int = field(default=166)  # 10 % more of keepalive_timeout

    def __post_init__(self):
        self.queue_factory = default_queue_factory(
            self.consumer.queues, self.publisher.exchange, self.consumer.prefetch_count
        )
        self.exchange_factory = default_exchange_factory(self.publisher.exchange)
        if self.publisher.exchange is not None:
            self.default_exchange = self.publisher.exchange.name
        else:
            self.default_exchange = ""


@load_configuration
@dataclass
class Config:
    database: Database
    rabbitmq: AMQP


def bootstrap_configuration(path: str = os.path.join(ROOT, "config.yml")) -> None:
    logger.info("loading configuration from file %s", path)
    with open(path, "r") as archivo:
        config = yaml.safe_load(archivo)
        load_configuration_data(config)


bootstrap_configuration()
