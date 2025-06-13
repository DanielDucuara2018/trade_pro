import logging

import click
import pandas as pd

from trade_pro.strategy.runner import run as strategy_runner
from trade_pro.strategy.utils import fetch_data

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


@click.group()
def cli():
    pass


@cli.command()
@click.option("--mode", required=True, type=click.Choice(["live", "backtest", "optimization"]))
@click.option("--name", required=True)
@click.option("--config", required=True)
def run(mode: str, name: str, config: str):
    logger.info(f"Running '{mode}' for strategy '{name}'")
    strategy_runner(mode, name, config)


@cli.command()
@click.option("--ticker", required=True, help="Ticker symbol (e.g., BTCUSDT)")
@click.option("--timeframe", required=True, help="Timeframe (e.g., 1h, 1d)")
@click.option("--start-date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
def fetch(ticker: str, timeframe: str, start_date: str, end_date: str | None = None):
    """Fetch market data for a given ticker and timeframe"""
    if end_date is None:
        end_date = pd.Timestamp.today()
    logger.info(
        f"Fetching data for {ticker}, timeframe={timeframe}, from {start_date} to {end_date}"
    )
    fetch_data(ticker, timeframe, pd.Timestamp(start_date), pd.Timestamp(end_date))


if __name__ == "__main__":
    cli()
