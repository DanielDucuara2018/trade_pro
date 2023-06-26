from __future__ import annotations

# import asyncio
import logging
from contextvars import ContextVar
from dataclasses import replace
from signal import SIGINT, SIGTERM
from typing import Any, Collection
from uuid import uuid4

import aio_pika

from trade_pro.rabbitmq.consumer import QueueFactory, consume
from trade_pro.rabbitmq.initialize import (
    declare_exchanges,
    declare_queues,
    init_rabbitmq,
)
from trade_pro.rabbitmq.publisher import ExchangeFactory
from trade_pro.rabbitmq.utils import Result, serialized_message, signal_event

logger = logging.getLogger(__name__)

request_id: ContextVar[str] = ContextVar("request_id")
correlation_id: ContextVar[str] = ContextVar("correlation_id")


class RMQHandler:
    def __init__(
        self,
        app_id: str,
        exchanges: Collection[aio_pika.Exchange],
    ):
        self.app_id = app_id
        self.exchanges = {exc.name: exc for exc in exchanges}

    async def publish(
        self,
        exchange: str,
        routing_key: str,
        body: Any,
        delivery_mode: aio_pika.DeliveryMode = aio_pika.DeliveryMode.PERSISTENT,
        **kwargs,
    ):
        kwargs.setdefault("headers", {})["request_id"] = request_id.get()
        try:
            message = serialized_message(
                body, app_id=self.app_id, delivery_mode=delivery_mode, **kwargs
            )
        except Exception:
            logger.exception("serialization error")
        else:
            try:
                await self.exchanges[exchange].publish(message, routing_key)
            except KeyError:
                raise RuntimeError("No echange %s", exchange)

    async def __call__(self, msg: aio_pika.Message):
        logger.info("message %s", msg)
        request_id.set(msg.headers.get("request_id", str(uuid4())))
        correlation_id.set(msg.correlation_id)
        logger.info(
            "Received message from %s. " "%s",
            msg.app_id,
            {"correlation_id": msg.correlation_id, "message_id": msg.message_id},
        )
        if msg.reply_to is not None:
            result: Result = Result(msg.correlation_id)
            result = replace(result, result={"msg": "hola mundo"})
            await self.publish(
                "", msg.reply_to, result, correlation_id=msg.correlation_id
            )


async def run(
    app_id: str,
    *,
    queues: QueueFactory = None,
    exchanges: ExchangeFactory = None,
):
    term_event = signal_event(SIGTERM, SIGINT)
    async with init_rabbitmq():

        handler = RMQHandler(
            app_id,
            await declare_exchanges(exchanges),
        )
        async with consume(await declare_queues(queues), handler):
            await term_event.wait()


# if __name__ == "__main__":
#     asyncio.run(run("test_consumer"))
