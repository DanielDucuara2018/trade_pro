import numpy as np
import pandas as pd
import pandas_ta as ta

from trade_pro.strategy.base import Base


class MASStrategy(Base):
    """
    A trading strategy based on Moving Average Spread (MAS), enhanced with RSI, MACD,
    and a daily SMA trend filter to determine entries and exits.

    Entry Conditions:
        - MAS crossover: The spread between fast and slow SMAs crosses from negative to positive.
        - RSI is below a specified threshold (indicating a potential oversold condition).
        - MACD is above the MACD signal line (momentum confirmation).
        - Daily close is above the daily SMA (bullish trend confirmation).

    Exit Conditions:
        - MAS crossover down: The spread between fast and slow SMAs crosses from positive to negative.

    Parameters:
        symbol (str): Trading pair symbol (e.g., "BTC/USDT").
        initial_balance (float): Starting capital.
        timeframes (list[str]): List of timeframes (must include "1h" and "1d").
        start_backtest_index (int): Index to begin backtesting from.
        fast (float): Period for fast SMA.
        slow (float): Period for slow SMA.
        rsi_period (float): Period for RSI.
        rsi_threshold (float): RSI threshold for entry (oversold filter).
        macd_fast (float): Fast EMA period for MACD.
        macd_slow (float): Slow EMA period for MACD.
        macd_signal (float): Signal line EMA period for MACD.
        trend_sma_period (float): Daily SMA period used for bullish trend filter.
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: int,
        timeframes: list[str],
        start_backtest_index: int,
        fast: int,
        slow: int,
        rsi_period: int,
        rsi_threshold: int,
        macd_fast: int,
        macd_slow: int,
        macd_signal: int,
        trend_sma_period: int,
        take_profit: float | None = None,
    ):
        super().__init__(
            symbol, initial_balance, timeframes, start_backtest_index=start_backtest_index
        )
        self.fast = fast
        self.slow = slow
        self.rsi_period = rsi_period
        self.rsi_threshold = rsi_threshold
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.trend_sma_period = trend_sma_period
        self.take_profit = (
            take_profit  # TODO add 1m or 4m data to track it price gets the take_profit
        )
        self.entry_price = None

    def check_config(self) -> bool:
        """
        Validates that the fast period is less than the slow period for MAS,
        and that MACD fast period is less than the MACD slow period.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        return self.fast < self.slow and self.macd_fast < self.macd_slow

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        (
            """
        Validates that the fast period is less than the slow period for MAS,
        and that MACD fast period is less than the MACD slow period.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
            """
        Validates that the fast period is less than the slow period for MAS,
        and that MACD fast period is less than the MACD slow period.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        )
        # get data
        df_1h = data["1h"]
        df_1d = data["1d"]

        # --- Moving Average Spread ---
        df_1h["FAST"] = ta.sma(df_1h["close"], length=self.fast)
        df_1h["SLOW"] = ta.sma(df_1h["close"], length=self.slow)
        df_1h["SPREAD"] = df_1h["FAST"] - df_1h["SLOW"]
        df_1h["SPREAD_SIGN"] = np.where(df_1h["SPREAD"] > 0, 1, -1)

        # --- RSI ---
        df_1h["RSI"] = ta.rsi(df_1h["close"], length=self.rsi_period)

        # --- MACD ---
        macd = ta.macd(df_1h["close"], self.macd_fast, self.macd_slow, self.macd_signal)
        df_1h["MACD"], df_1h["MACD_SIGNAL"] = (
            macd[f"MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"],
            macd[f"MACDs_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"],
        )

        # --- Daily SMA Trend Filter ---
        df_1d[f"SMA{self.trend_sma_period}"] = ta.sma(df_1d["close"], self.trend_sma_period)
        df_1d["BULLISH_TREND"] = df_1d["close"] > df_1d[f"SMA{self.trend_sma_period}"]
        df_1h["BULLISH_TREND"] = (
            df_1d["BULLISH_TREND"].shift(1).reindex(df_1h.index, method="ffill")
        )

        return df_1h

    def entry_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        """
        Determines whether to enter a position.

        Conditions:
            - No open position.
            - MAS spread changes from negative to positive over last 3 candles.
            - RSI is below threshold (potential oversold bounce).
            - MACD > MACD signal (bullish momentum).
            - Daily bullish trend (price > daily SMA).

        Args:
            df (pd.DataFrame): 1h OHLCV + indicator DataFrame.
            index (int): Row index to evaluate.

        Returns:
            bool: True if entry conditions are met.
        """
        row = df.iloc[index]
        prev = df.iloc[index - 1]
        prev2 = df.iloc[index - 2]

        entry_condition = (
            not self.position
            and prev2["SPREAD_SIGN"] == -1
            and prev["SPREAD_SIGN"] == -1
            and row["SPREAD_SIGN"] == 1
            and row["RSI"] < self.rsi_threshold
            and row["MACD"] > row["MACD_SIGNAL"]
            and row["BULLISH_TREND"]
        )

        if entry_condition:
            self.entry_price = row["close"]

        return entry_condition

    def exit_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        """
        Determines whether to exit a position.

        Conditions:
            - MAS spread changes from positive to negative over last 3 candles.

        Args:
            df (pd.DataFrame): 1h OHLCV + indicator DataFrame.
            index (int): Row index to evaluate.

        Returns:
            bool: True if exit conditions are met.
        """
        row = df.iloc[index]
        prev = df.iloc[index - 1]
        prev2 = df.iloc[index - 2]

        percentage_gain = (
            (row["close"] - self.entry_price) / self.entry_price if self.entry_price else 0
        )

        exit_condition = self.position and (
            prev2["SPREAD_SIGN"] == 1
            and prev["SPREAD_SIGN"] == 1
            and row["SPREAD_SIGN"] == -1
            or (self.take_profit is not None and percentage_gain >= self.take_profit / 100)
        )

        if exit_condition:
            self.exit_price = None

        return exit_condition
