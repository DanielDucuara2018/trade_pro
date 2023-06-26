from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from signal import Signals
from typing import (
    Any,
    AsyncContextManager,
    Awaitable,
    Callable,
    Generic,
    Literal,
    Mapping,
    Optional,
    Sequence,
    TypeVar,
    Union,
    cast,
)

import aio_pika
import orjson
from apischema import Undefined, UndefinedType, schema, serialize
from apischema.metadata import required

# from trade_pro.config import Config
from trade_pro.rabbitmq.errors import StoppedCounter

logger = logging.getLogger(__name__)

WRAPPER_ATTR = "_wrapper"
T = TypeVar("T")


@dataclass(frozen=True)
class Body:
    method: str
    params: Union[Sequence[Any], Mapping[str, Any]]
    id: Optional[str] = None
    jsonrpc: Literal["2.0"] = field(default="2.0", metadata=required)


@dataclass
class Call(Generic[T]):
    method: str
    params: Union[Sequence[Any], Mapping[str, Any]]

    def body(self, id: str = None) -> Body:
        return Body(self.method, self.params, id)


@schema(min_props=2, max_props=2)
@dataclass(frozen=True)
class Result(Generic[T]):
    id: Optional[str]
    result: Union[T, UndefinedType] = Undefined
    # error: Union[Exception, UndefinedType] = Undefined

    # def get(self) -> T:
    #     if self.error is not Undefined:
    #         raise self.error
    #     else:
    #         assert self.result is not Undefined
    #         return self.result


class AttrWrapper(Generic[T]):
    def __init__(self, wrapper: Callable[[], T]):
        super().__setattr__(WRAPPER_ATTR, wrapper)

    def __getattribute__(self, name):
        return getattr(super().__getattribute__(WRAPPER_ATTR)(), name)

    def __setattr__(self, name, value):
        setattr(super().__getattribute__(WRAPPER_ATTR)(), name, value)


def attr_wrapper(wrapper: Callable[[], T]) -> T:
    return cast(T, AttrWrapper(wrapper))


def serialized_message(body: Union[Body, Result], **kwargs) -> aio_pika.Message:
    return aio_pika.Message(
        orjson.dumps(serialize(body), option=orjson.OPT_NON_STR_KEYS),
        content_type="application/json",
        # expiration=Config.rabbitmq.message_expiration,
        **kwargs,
    )


def signal_event(*signals: Signals) -> asyncio.Event:
    """Event set when the following signals are raised."""
    event = asyncio.Event()
    for signal in signals:

        def handler(signal=signal, event=event):
            logger.info("%s received", signal.name)
            event.set()

        asyncio.get_running_loop().add_signal_handler(signal, handler)
    return event


def check_initialized(channel: Optional[aio_pika.Channel]) -> aio_pika.Channel:
    if channel is None:
        raise RuntimeError("RabbitMQ is not initialized")
    return channel


async def run_until(actx_manager: AsyncContextManager, until: Awaitable[T]) -> T:
    async with actx_manager:
        return await until


class TaskCounter:
    def __init__(self):
        self.count = 0
        self.stopped = False
        self.no_more_tasks = asyncio.Event()

    def __enter__(self):
        if self.stopped:
            raise StoppedCounter
        self.count += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.count -= 1
        if self.stopped and self.count == 0:
            self.no_more_tasks.set()

    async def stop(self):
        self.stopped = True
        if self.count > 0:
            await self.no_more_tasks.wait()
