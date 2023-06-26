import asyncio
import logging
from typing import Dict, Optional
from uuid import uuid4

import aio_pika
import orjson

from trade_pro.rabbitmq.initialize import init_rabbitmq, read_channel, write_channel
from trade_pro.rabbitmq.utils import Call, Result, serialized_message

logger = logging.getLogger(__name__)

_requester: Optional["Requester"] = None


class Requester:
    def __init__(self, write_channel: aio_pika.Channel, queue: aio_pika.Queue):
        self.write_channel = write_channel
        self.queue = queue
        self.results: Dict[str, "asyncio.Future[aio_pika.Message]"] = {}

    async def callback(self, message: aio_pika.IncomingMessage):
        try:
            self.results[message.correlation_id].set_result(message)
        except KeyError:
            await message.reject()
        else:
            await message.ack()

    async def __call__(
        self, message: aio_pika.Message, routing_key: str, exchange: str = ""
    ) -> aio_pika.Message:
        if message.correlation_id is None:
            message.correlation_id = str(uuid4())
        correlation_id = message.correlation_id
        message.reply_to = self.queue.name
        future = asyncio.get_running_loop().create_future()
        self.results[correlation_id] = future
        if exchange:
            exchange_ = await self.write_channel.get_exchange(exchange)
        else:
            exchange_ = self.write_channel.default_exchange
        await exchange_.publish(message, routing_key)
        try:
            return await future
        finally:
            self.results.pop(correlation_id)


async def requester(
    call: Call, app_id: str, routing_key: str, *, exchange: str = ""
) -> Result:
    global _requester
    if _requester is None:
        queue = await read_channel.declare_queue("", durable=True, exclusive=True)
        _requester = Requester(write_channel, queue)
        await queue.consume(_requester.callback)

    body_call = call.body()
    logger.info(
        "Message to send: {method: %s, params: %s}", body_call.method, body_call.params
    )
    message = serialized_message(
        body_call, headers={"request_id": str(uuid4())}, app_id=app_id
    )

    response = await _requester(message, routing_key, exchange)
    json_body = orjson.loads(response.body)
    logger.info("Response: %s", json_body)

    return response


async def run(
    app_id: str,
    routing_key: str,
    call: Call,
) -> Result:
    async with init_rabbitmq():
        return await requester(call, app_id, routing_key)


# if __name__ == "__main__":
#     asyncio.run(run("test_producer", "trade"))
