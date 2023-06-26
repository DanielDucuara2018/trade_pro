import asyncio
import logging
import subprocess

import click

from trade_pro.strategy import get_module

logger = logging.getLogger(__name__)


def run(mode: str, strategy_name: str):
    logger.info("Running main proccess")
    subprocess.Popen([mode, "--name", strategy_name])


@click.command()
@click.option("--name", required=True, type=str)
def strategy(name):
    logger.info("Running strategy proccess %s", name)
    module = get_module(name)
    logger.info("Found module strategy %s", module)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(module.init.run())


@click.command()
@click.option("--name", required=True, type=str)
def back_testing(name):
    logger.info("Running back_testing proccess strategy %s", name)
    module = get_module(name)
    logger.info("Found module strategy %s", module)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(module.init.back_testing())


@click.command()
@click.option("--name", required=True, type=str)
def sginals(name):
    pass
