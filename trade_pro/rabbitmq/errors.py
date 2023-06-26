from __future__ import annotations


class StoppedCounter(Exception):
    pass


class Reject(Exception):
    pass


class Nack(Exception):
    pass
