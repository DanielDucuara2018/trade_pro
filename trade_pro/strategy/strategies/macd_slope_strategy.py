import pandas as pd
import pandas_ta as ta

from trade_pro.strategy.strategies.atr_strategy_base import ATRStrategyBase


class MACDSlopeStrategy(ATRStrategyBase):
    """
    A MACD-based trading strategy using slope for exit signal.

    Entry Condition:
        - MACD fast line crosses above the signal line (bullish crossover)

    Exit Condition:
        - Slope of MACD line changes from positive to <= 0

    Args:
        symbol (str): Trading symbol (e.g., 'BTCUSDT').
        initial_balance (float): Starting account balance.
        timeframes (list[str]): List of timeframes to use (expects '1h' in this version).
        start_backtest_index (int): Index to start backtesting from.
        macd_fast (int): Fast period for MACD.
        macd_slow (int): Slow period for MACD.
        macd_signal (int): Signal period for MACD.
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float,
        timeframes: list[str],
        start_backtest_index: int,
        macd_fast: int,
        macd_slow: int,
        macd_signal: int,
        atr_period: int = 14,
        atr_stop_multiplier: float = 2.0,
        risk_reward_ratio: float = 2.0,
        use_atr_stops: bool = False,
        **kwargs,
    ):
        super().__init__(
            symbol, initial_balance, timeframes, start_backtest_index=start_backtest_index, **kwargs
        )
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.atr_period = atr_period
        self.atr_stop_multiplier = atr_stop_multiplier
        self.risk_reward_ratio = risk_reward_ratio
        self.use_atr_stops = use_atr_stops

    def check_config(self) -> bool:
        return self.macd_fast < self.macd_slow

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        df = data["1d"]
        macd_df = ta.macd(
            df["close"], fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal
        )

        df["MACD"] = macd_df[f"MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"]
        df["MACD_signal"] = macd_df[f"MACDs_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"]
        df["MACD_slope"] = (
            df["MACD"].diff() / df["MACD"].index.to_series().diff().dt.total_seconds()
        )

        # Calculate ATR for stop loss calculation
        df["ATR"] = ta.atr(df["high"], df["low"], df["close"], length=self.atr_period)

        return df

    def entry_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        row = df.iloc[index]
        prev = df.iloc[index - 1]
        prev2 = df.iloc[index - 2]

        return (
            not self.position
            and prev2["MACD"] < prev2["MACD_signal"]
            and prev["MACD"] < prev["MACD_signal"]
            and row["MACD"] > row["MACD_signal"]
        )

    def exit_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        if not self.position:
            return False

        row = df.iloc[index]

        # Check stop loss and take profit first (strategy-specific logic)
        if (
            self.use_atr_stops
            and hasattr(self, "_current_single_trade")
            and self._current_single_trade
        ):
            trade = self._current_single_trade
            current_price = row["close"]

            # Stop loss check
            if trade.stop_loss > 0 and current_price <= trade.stop_loss:
                return True

            # Take profit check
            if trade.take_profit > 0 and current_price >= trade.take_profit:
                return True

        # Original exit: slope turns negative
        prev = df.iloc[index - 1]
        prev2 = df.iloc[index - 2]

        return prev2["MACD_slope"] > 0 and prev["MACD_slope"] > 0 and row["MACD_slope"] <= 0
