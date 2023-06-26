from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import TYPE_CHECKING, Awaitable, Callable, Collection, Mapping

import aio_pika

from trade_pro.rabbitmq.errors import Nack, Reject, StoppedCounter
from trade_pro.rabbitmq.utils import TaskCounter, run_until

if TYPE_CHECKING:
    from trade_pro.rabbitmq.config import ExchangeOptions, QueueOptions


logger = logging.getLogger(__name__)

MsgHandler = Callable[[aio_pika.Message], Awaitable[None]]
QueueFactory = Callable[[aio_pika.Channel], Awaitable[Collection[aio_pika.Queue]]]


@asynccontextmanager
async def consume_queue(queue: aio_pika.Queue, handler: MsgHandler):
    task_counter = TaskCounter()

    async def callback(message: aio_pika.IncomingMessage):
        with task_counter:
            message_id = message.message_id
            try:
                await handler(message)
                await message.ack()
            except (StoppedCounter, Nack):
                logger.debug("Message %s nacked, requeued", message_id)
                await message.nack()
            except Reject:
                logger.debug("Message %s rejected.", message_id)
                await message.reject()
            except Exception as e:
                logger.exception("Error while consuming message %s: %s", message_id, e)
                await message.reject()

    consumer_tag = await queue.consume(callback)
    logger.info("Start consuming queue: %s", queue.name)
    try:
        yield
    finally:
        logger.debug("Cancelling consuming queue: %s", queue.name)
        await queue.cancel(consumer_tag)
        logger.debug("Wait for remaining tasks on queue: %s", queue.name)
        await task_counter.stop()
        logger.info("Stopped consuming queue: %s", queue.name)


@asynccontextmanager
async def consume(queues: Collection[aio_pika.Queue], handler: MsgHandler):
    logger.info("Consumer started.")
    stop_event = asyncio.Event()
    tasks = [
        asyncio.get_running_loop().create_task(
            run_until(consume_queue(queue, handler), stop_event.wait())
        )
        for queue in queues
    ]
    try:
        yield
    finally:
        stop_event.set()
        logger.debug("Consumer waiting to stop.")
        await asyncio.gather(*tasks)
        logger.info("Consumer stopped.")


def default_queue_factory(
    queue_opts: Mapping[str, QueueOptions],
    exchange: ExchangeOptions = None,
    prefetch_count: int = 1,
) -> QueueFactory:
    async def factory(channel: aio_pika.Channel) -> Collection[aio_pika.Queue]:
        async def declare_queue(name: str, opts: QueueOptions) -> aio_pika.Queue:
            logger.debug("Creating queue %s", name)
            queue = await channel.declare_queue(name, **asdict(opts))
            if exchange:
                await queue.bind(exchange.name, name)
            return queue

        await channel.set_qos(prefetch_count=prefetch_count)
        return await asyncio.gather(
            *(declare_queue(name, opts) for name, opts in queue_opts.items())
        )

    return factory
