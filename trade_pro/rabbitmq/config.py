from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from apischema.metadata import flatten


@dataclass
class QueueOptions:
    durable: bool = True
    exclusive: bool = False
    passive: bool = False
    auto_delete: bool = False


@dataclass
class ExchangeOptions:
    name: str
    durable: bool = True
    auto_delete: bool = False
    internal: bool = False
    passive: bool = False


@dataclass
class RMQConnectionOptions:
    host: str
    login: str
    password: str
    # virtualhost: str = "vhost"

    port: int
    ssl: bool = False
    ssl_options: Optional[Mapping[str, Any]] = None


@dataclass
class Consumer:
    connection: RMQConnectionOptions = field(metadata=flatten)
    queues: Mapping[str, QueueOptions] = field(default_factory=dict)
    prefetch_count: int = 1
    callback_queue: Optional[str] = None


@dataclass
class Publisher:
    connection: RMQConnectionOptions = field(metadata=flatten)
    exchange: Optional[ExchangeOptions] = None
    routing_key: Optional[str] = None
