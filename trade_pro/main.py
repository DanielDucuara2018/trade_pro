import logging

import click

from trade_pro.strategy.runner import run

logger = logging.getLogger(__name__)


@click.group()
def console():
    pass


@console.command()
@click.option("--strategy", required=True, type=str)
def strategy(strategy):
    logger.info(f"Running strategy {strategy}")
    run("strategy", strategy)


@console.command()
@click.option("--strategy", required=True, type=str)
def back_testing(strategy):
    logger.info(f"Running back testing for strategy {strategy}")
    run("back-testing", strategy)


def main():
    logger.info("Running main process")
    while True:
        pass


if __name__ == "__main__":
    main()
