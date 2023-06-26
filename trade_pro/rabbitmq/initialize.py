from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from typing import AsyncIterator, Collection, Optional, Tuple

import aio_pika

from trade_pro.config import Config
from trade_pro.rabbitmq.config import RMQConnectionOptions
from trade_pro.rabbitmq.consumer import QueueFactory
from trade_pro.rabbitmq.publisher import ExchangeFactory
from trade_pro.rabbitmq.utils import attr_wrapper, check_initialized

logger = logging.getLogger(__name__)

_read_connection: Optional[aio_pika.Connection] = None
_write_connection: Optional[aio_pika.Connection] = None
_read_channel: Optional[aio_pika.Channel] = None
_write_channel: Optional[aio_pika.Channel] = None

read_channel = attr_wrapper(lambda: check_initialized(_read_channel))
write_channel = attr_wrapper(lambda: check_initialized(_write_channel))


async def declare_exchanges(
    factory: ExchangeFactory = None,
) -> Collection[aio_pika.Exchange]:
    if factory is None:
        factory = Config.rabbitmq.exchange_factory
    return [*(await factory(write_channel)), write_channel.default_exchange]


async def declare_queues(factory: QueueFactory = None) -> Collection[aio_pika.Queue]:
    if factory is None:
        factory = Config.rabbitmq.queue_factory
    return await factory(read_channel)


@dataclass
class RMQConnection:
    opts: RMQConnectionOptions
    name: str
    conn: aio_pika.Connection = field(init=False)

    async def on_connection_close(self, *args):
        logger.debug("Executing on_connection_close callback")
        if asyncio.exceptions.CancelledError in [type(arg) for arg in args]:
            logger.debug("Not trying to reconnect")
            return
        await self.connect()

    async def connect(self) -> aio_pika.Connection:
        while True:
            try:
                logger.debug("Connection to broker %s...", self.name)
                host = self.opts.host
                self.conn = await aio_pika.connect(
                    client_properties={"connection_name": f"{self.name} connection"},
                    **asdict(self.opts),
                )
                self.conn.close_callbacks.add(self.on_connection_close)
                return self.conn
            except (aio_pika.AMQPException, ConnectionError):
                logger.error("Failed to connect to host %s: Retrying", host)
                await asyncio.sleep(Config.rabbitmq.time_to_reconnect)


@asynccontextmanager
async def read_write_connections(
    read: RMQConnectionOptions, write: RMQConnectionOptions
) -> AsyncIterator[Tuple[aio_pika.Connection, aio_pika.Connection]]:
    read_conn, write_conn = await asyncio.gather(
        RMQConnection(read, "consumer").connect(),
        RMQConnection(write, "publisher").connect(),
    )
    async with write_conn, read_conn:
        yield read_conn, write_conn


@asynccontextmanager
async def init_rabbitmq():
    global _read_connection, _write_connection, _read_channel, _write_channel
    if _read_connection is not None:
        raise RuntimeError("RabbitMq already initialized")
    amqp = Config.rabbitmq
    async with read_write_connections(
        amqp.consumer.connection, amqp.publisher.connection
    ) as (_read_connection, _write_connection):
        _read_channel, _write_channel = await asyncio.gather(
            _read_connection.channel(), _write_connection.channel()
        )
        try:
            yield
        finally:
            _read_connection, _write_connection = None, None
            _read_channel, _write_channel = None, None
