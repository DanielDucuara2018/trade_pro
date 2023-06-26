import asyncio
import logging

import click

from trade_pro.rabbitmq.runner import run as rmq_runner
from trade_pro.strategy.runner import run as strategy_runner

logger = logging.getLogger(__name__)


@click.group()
def console():
    pass


@console.command()
@click.option("--name", required=True, type=str)
def strategy(name):
    logger.info(f"Running strategy {name} on background")
    strategy_runner("strategy", name)


@console.command()
@click.option("--name", required=True, type=str)
def back_testing(name):
    logger.info(f"Running back testing for strategy {name} on background")
    strategy_runner("back-testing", name)


@console.command()
@click.option("--name", required=True, type=str)
def signals(name):
    logger.info(f"Running signals for strategy {name} on background")
    strategy_runner("signals", name)


def main():
    logger.info("Running main process")
    asyncio.run(rmq_runner("trade_pro"))


if __name__ == "__main__":
    main()
