import asyncio
import logging
import subprocess

import click

from trade_pro.strategy import get_module

logger = logging.getLogger(__name__)


def run(mode: str, strategy_name: str):
    logger.info("Running main proccess")
    subprocess.Popen([mode, "--strategy", strategy_name])


@click.command()
@click.option("--strategy", required=True, type=str)
def strategy(strategy):
    logger.info("Running strategy proccess %s", strategy)
    module = get_module(strategy)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(module.init.run())


@click.command()
@click.option("--strategy", required=True, type=str)
def back_testing(strategy):
    logger.info("Running back_testing proccess strategy %s", strategy)
    module = get_module(strategy)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(module.init.back_testing())
