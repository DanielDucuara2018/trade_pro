import logging

import click

from trade_pro.strategy.runner import run as strategy_runner

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--mode",
    required=True,
    type=click.Choice(["live", "backtest", "optimization"]),
    help="Execution mode",
)
@click.option("--name", required=True, type=str, help="Strategy name")
@click.option("--config", required=True, type=str, default=None, help="Cnfig file name")
def console(mode: str, name: str, config: str):
    """Run strategy operations in different modes"""
    logger.info(f"Running '{mode}' for strategy '{name}'")
    strategy_runner(mode, name, config)


if __name__ == "__main__":
    console()
