import datetime
import json
import logging
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import ccxt
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import colormaps

if TYPE_CHECKING:
    from trade_pro.strategy.base import Trade

CURRENT_DIR = Path(__file__).parent
IMAGES_DIR = CURRENT_DIR.joinpath("images")
DATA_DIR = CURRENT_DIR.joinpath("data")
CONFIG_DIR = CURRENT_DIR.joinpath("config")

exchange = ccxt.binance()

logger = logging.getLogger(__name__)


def fetch_candles(symbol: str, timeframe: str, limit=10, retry: int = 5) -> pd.DataFrame:
    time.sleep(10)
    logger.info("Fetching candles for %s, timeframe=%s", symbol, timeframe)
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except ccxt.RequestTimeout as e:
        logger.warning("Error fetching candle data")
        if retry <= 0:
            raise e
        return fetch_candles(symbol, timeframe, limit, retry - 1)

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df.drop_duplicates()
    logger.info("Fetched %d candles for %s, timeframe=%s", len(df), symbol, timeframe)
    return df


def update_data(df: pd.DataFrame, df_new: pd.DataFrame) -> pd.DataFrame:
    df_combined = pd.concat([df, df_new])
    df_combined = df_combined[~df_combined.index.duplicated(keep="last")]
    return df_combined.sort_index()


def wait_for_next_candle(*, timeframe: str = "1h") -> None:
    now = datetime.datetime.now()

    # Parse timeframe like "1m", "5m", "1h", "4h", "1d"
    match = re.fullmatch(r"(\d+)([mhd])", timeframe)
    if not match:
        raise ValueError(f"Unsupported timeframe format: {timeframe}")

    value, unit = int(match.group(1)), match.group(2)

    # Convert timeframe to total seconds
    if unit == "m":
        interval_seconds = value * 60
    elif unit == "h":
        interval_seconds = value * 3600
    elif unit == "d":
        interval_seconds = value * 86400
    else:
        raise ValueError(f"Unsupported timeframe unit: {unit}")

    # Compute seconds since midnight
    seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second

    # Compute time until next aligned candle
    elapsed = seconds_since_midnight % interval_seconds
    wait_seconds = interval_seconds - elapsed

    # Wait with buffer
    logger.info("Wating %s until next data fecth", wait_seconds)
    time.sleep(wait_seconds + 2)


def get_data(symbol: str, timeframe: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR.joinpath(f"{symbol.replace('/', '')}_{timeframe}.csv"))
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    return df.drop_duplicates()


def fetch_data(
    symbol: str, timeframe: str, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    ohlcv = []
    limit = 1000
    exchange = ccxt.binance()
    while start_date < end_date:
        ohlcv += exchange.fetch_ohlcv(
            symbol, since=start_date.value // 10**6, limit=limit, timeframe=timeframe
        )
        start_date += pd.Timedelta(1000, timeframe[-1])

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df.drop_duplicates()
    if df.index.duplicated().any():
        print(f"There are duplicated dates {df[df.index.duplicated()]}")
    df.to_csv(DATA_DIR.joinpath(f"{symbol.replace('/', '')}_{timeframe}.csv"))


def load_strategy_config(file_name: str) -> dict[str, Any]:
    config_path = CONFIG_DIR.joinpath(f"{file_name}.json")

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def plot_price_chart(
    symbol: str,
    strategy_name: str,
    df: pd.DataFrame,
    trades: dict[str, "Trade"],
) -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(14, 6))
    plt.plot(df["close"], label="Close Price", alpha=0.7, color="gray")

    # Convert trades dict to list for plotting
    trade_list = list(trades.values())

    # Use a colormap to differentiate trades
    cmap = colormaps["tab20"].resampled(len(trade_list))  # tab20 or any other colormap
    for i, trade in enumerate(trade_list):
        entry_time = trade.entry_time
        exit_time = trade.exit_time
        entry_price = trade.entry_price
        exit_price = trade.exit_price

        # Draw a vertical line at entry and exit, with unique colors
        plt.axvline(entry_time, color=cmap(i), linestyle="--", alpha=0.8)
        plt.axvline(exit_time, color=cmap(i), linestyle=":", alpha=0.8)

        # Optionally, mark entry/exit with dots
        plt.scatter(
            entry_time, entry_price, color=cmap(i), marker="^", label=f"Entry {i + 1}", s=60
        )
        plt.scatter(exit_time, exit_price, color=cmap(i), marker="v", label=f"Exit {i + 1}", s=60)

    plt.title(f"{strategy_name} Strategy Backtest")
    plt.grid(True)
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.tight_layout()
    plt.savefig(IMAGES_DIR.joinpath(f"{symbol.replace('/', '')}_{strategy_name}_strategy.png"))
    plt.close()


def plot_equity_curve(symbol: str, strategy_name: str, trades: dict[str, "Trade"]) -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(12, 6))

    # Extract old_balance values from Trade objects
    trade_list = list(trades.values())
    old_balances = [trade.old_balance for trade in trade_list if trade.old_balance is not None]

    plt.plot(old_balances)
    plt.title(f"{strategy_name} Strategy Equity Curve")
    plt.xlabel("Trades")
    plt.ylabel("Balance")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(IMAGES_DIR.joinpath(f"{symbol.replace('/', '')}_{strategy_name}_equity_curve.png"))
