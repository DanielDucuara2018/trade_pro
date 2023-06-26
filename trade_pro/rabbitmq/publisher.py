from __future__ import annotations

import logging
from dataclasses import asdict
from typing import TYPE_CHECKING, Awaitable, Callable, Collection

import aio_pika

if TYPE_CHECKING:
    from trade_pro.rabbitmq.config import ExchangeOptions


logger = logging.getLogger(__name__)

ExchangeFactory = Callable[[aio_pika.Channel], Awaitable[Collection[aio_pika.Exchange]]]


def default_exchange_factory(exchange: ExchangeOptions = None) -> ExchangeFactory:
    async def factory(channel: aio_pika.Channel) -> Collection[aio_pika.Exchange]:
        if exchange:
            logger.debug("Declaring exchange %s.", exchange.name)
            return (await channel.declare_exchange(**asdict(exchange)),)
        return ()

    return factory
