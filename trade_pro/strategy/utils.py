import datetime
import json
import time
from pathlib import Path
from typing import Any

import ccxt
import pandas as pd

CURRENT_DIR = Path(__file__).parent
IMAGES_DIR = CURRENT_DIR.joinpath("images")
DATA_DIR = CURRENT_DIR.joinpath("data")
CONFIG_DIR = CURRENT_DIR.joinpath("config")

exchange = ccxt.binance()


def fetch_candles(symbol: str, timeframe: str, limit=10) -> pd.DataFrame:
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df.drop_duplicates()
    return df


def update_data(df: pd.DataFrame, df_new: pd.DataFrame) -> pd.DataFrame:
    df_combined = pd.concat([df, df_new])
    df_combined = df_combined[~df_combined.index.duplicated(keep="last")]
    return df_combined.sort_index()


def wait_for_next_candle(*, timeframe: str = "1h") -> None:
    now = datetime.datetime.now()
    if timeframe == "1h":
        wait_seconds = 3600 - (now.minute * 60 + now.second)
    time.sleep(wait_seconds + 2)  # buffer time


def get_data(symbol: str, timeframe: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR.joinpath(f"{symbol.replace('/', '')}_{timeframe}.csv"))
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    return df.drop_duplicates()


def fetch_data(
    symbol: str, timeframe: str, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> None:
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
