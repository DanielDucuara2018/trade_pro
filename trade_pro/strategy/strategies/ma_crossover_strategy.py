import pandas as pd
import pandas_ta as ta

from trade_pro.strategy.strategies.atr_strategy_base import ATRStrategyBase


class MACrossoverStrategy(ATRStrategyBase):
    """
    Moving Average Crossover trading strategy.

    Entry Condition:
        - Fast MA crosses above Slow MA (bullish crossover)

    Exit Condition:
        - Fast MA crosses below Slow MA (bearish crossover)
        OR
        - Stop loss / Take profit hit

    Args:
        symbol (str): Trading symbol (e.g., 'BTCUSDT').
        initial_balance (float): Starting account balance.
        timeframes (list[str]): List of timeframes to use.
        start_backtest_index (int): Index to start backtesting from.
        fast_period (int): Fast MA period.
        slow_period (int): Slow MA period.
        ma_type (str): Type of MA ('SMA' or 'EMA').
        atr_period (int): ATR period for stop loss calculation.
        atr_stop_multiplier (float): ATR multiplier for stop distance.
        risk_reward_ratio (float): Risk/reward ratio for take profit.
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float,
        timeframes: list[str],
        start_backtest_index: int,
        fast_period: int = 10,
        slow_period: int = 50,
        ma_type: str = "EMA",
        atr_period: int = 14,
        atr_stop_multiplier: float = 2.0,
        risk_reward_ratio: float = 2.5,
        **kwargs,
    ):
        super().__init__(
            symbol, initial_balance, timeframes, start_backtest_index=start_backtest_index, **kwargs
        )
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.ma_type = ma_type.upper()
        self.atr_period = atr_period
        self.atr_stop_multiplier = atr_stop_multiplier
        self.risk_reward_ratio = risk_reward_ratio

    def check_config(self) -> bool:
        """Validate configuration parameters"""
        return (
            self.fast_period < self.slow_period
            and self.fast_period > 0
            and self.ma_type in ["SMA", "EMA"]
        )

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Calculate fast and slow MAs, and ATR"""
        df = data[self.timeframes[0]]

        # Calculate MAs
        if self.ma_type == "SMA":
            df["MA_fast"] = ta.sma(df["close"], length=self.fast_period)
            df["MA_slow"] = ta.sma(df["close"], length=self.slow_period)
        else:  # EMA
            df["MA_fast"] = ta.ema(df["close"], length=self.fast_period)
            df["MA_slow"] = ta.ema(df["close"], length=self.slow_period)

        # ATR for stop loss
        df["ATR"] = ta.atr(df["high"], df["low"], df["close"], length=self.atr_period)

        return df

    def entry_condition(self, df: pd.DataFrame, *, index: int = -1) -> bool:
        """Entry when fast MA crosses above slow MA"""
        if self.position:
            return False
        if 0 <= index < 1:
            # Not enough history yet at the very start of a backtest — guards
            # against df.iloc[index - 1] wrapping around to the DataFrame's last
            # row. Only applies to absolute (backtest) indices; live mode's
            # negative relative index is unaffected.
            return False

        row = df.iloc[index]
        prev = df.iloc[index - 1]

        # Golden cross: fast MA crosses above slow MA
        return prev["MA_fast"] <= prev["MA_slow"] and row["MA_fast"] > row["MA_slow"]

    def exit_condition(self, df: pd.DataFrame, *, index: int = -1) -> bool:
        """Exit when fast MA crosses below slow MA"""
        if not self.position:
            return False

        row = df.iloc[index]
        prev = df.iloc[index - 1]

        # Death cross: fast MA crosses below slow MA
        return prev["MA_fast"] >= prev["MA_slow"] and row["MA_fast"] < row["MA_slow"]

    def _get_trade_metadata(self, row: pd.Series, atr_value: float, entry_price: float) -> dict:
        """Add MA-specific metadata"""
        metadata = super()._get_trade_metadata(row, atr_value, entry_price)
        metadata["ma_fast"] = row["MA_fast"]
        metadata["ma_slow"] = row["MA_slow"]
        return metadata
