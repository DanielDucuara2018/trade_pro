import pandas as pd
import pandas_ta as ta

from trade_pro.strategy.base import Base


class MACDStrategy(Base):
    """
    A trading strategy combining MACD, RSI, EMA, and ADX indicators to identify trend-based
    entry and exit signals using 1-hour price data.

    Entry Conditions:
        - No position is open.
        - Price is above the EMA (trend filter).
        - ADX is above the threshold (trend strength confirmation).
        - RSI crosses above the entry threshold.
        - MACD crosses above the MACD signal line.

    Exit Conditions:
        - A position is open.
        - RSI crosses below the exit threshold OR
        - MACD crosses below the MACD signal line.

    Parameters:
        symbol (str): Trading pair symbol, e.g. "BTC/USDT".
        initial_balance (float): Starting capital.
        timeframes (list[str]): List of timeframes used (must include "1h").
        start_backtest_index (int): Index to begin backtesting from.
        macd_fast (int): Fast EMA period for MACD.
        macd_slow (int): Slow EMA period for MACD.
        macd_signal (int): Signal line EMA period for MACD.
        rsi_period (int): Period for RSI calculation.
        rsi_threshold_entry (int): RSI level to trigger entry.
        rsi_threshold_exit (int): RSI level to trigger exit.
        ema_period (int): Period for trend EMA.
        adx_period (int): Period for ADX indicator.
        adx_treshold (int): Minimum ADX level to validate trend strength.
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
        rsi_period: int,
        rsi_threshold_entry: int,
        rsi_threshold_exit: int,
        ema_period: int,
        adx_period: int,
        adx_treshold: int,
    ):
        super().__init__(
            symbol, initial_balance, timeframes, start_backtest_index=start_backtest_index
        )
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.rsi_period = rsi_period
        self.rsi_threshold_entry = rsi_threshold_entry
        self.rsi_threshold_exit = rsi_threshold_exit
        self.ema_period = ema_period
        self.adx_period = adx_period
        self.adx_treshold = adx_treshold

    def check_config(self) -> bool:
        """
        Ensures MACD fast period is less than the slow period for valid MACD calculation.

        Returns:
            bool: True if config is valid, else False.
        """
        return self.macd_fast < self.macd_slow

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Computes technical indicators required for entry and exit conditions.

        Args:
            data (dict[str, pd.DataFrame]): Dictionary of OHLCV data by timeframe.

        Returns:
            pd.DataFrame: 1h DataFrame with added indicator columns.
        """
        # get data
        df_1h = data["1h"]

        # --- MACD ---
        macd = ta.macd(df_1h["close"], self.macd_fast, self.macd_slow, self.macd_signal)
        df_1h["MACD"], df_1h["MACD_SIGNAL"] = (
            macd[f"MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"],
            macd[f"MACDs_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"],
        )
        # --- RSI ---
        df_1h["RSI"] = ta.rsi(df_1h["close"], length=self.rsi_period)

        # --- EMA ---
        df_1h["EMA"] = ta.ema(df_1h["close"], length=self.ema_period)

        # --- ADX ---
        df_1h["ADX"] = ta.adx(df_1h["high"], df_1h["low"], df_1h["close"], length=self.adx_period)[
            f"ADX_{self.adx_period}"
        ]

        return df_1h

    def entry_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        """
        Determines whether to enter a trade.

        Conditions:
            - No position is open.
            - Price is above EMA (trend confirmation).
            - ADX above threshold (trend strength).
            - RSI crosses above entry threshold.
            - MACD crosses above signal line.

        Args:
            df (pd.DataFrame): Indicator-enriched OHLCV data.
            index (int): Index to evaluate.

        Returns:
            bool: True if entry conditions are met, else False.
        """
        row = df.iloc[index]
        prev = df.iloc[index - 1]

        return (
            not self.position
            and row["close"] > row["EMA"]  # Trend filter
            and row["ADX"] > self.adx_treshold  # Trend strength
            and prev["RSI"] < self.rsi_threshold_entry < row["RSI"]  # RSI crossover up
            and prev["MACD"] < prev["MACD_SIGNAL"]
            and row["MACD"] > row["MACD_SIGNAL"]  # MACD crossover
        )

    def exit_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        """
        Determines whether to exit a trade.

        Conditions:
            - RSI crosses below the exit threshold, OR
            - MACD crosses below the signal line.

        Args:
            df (pd.DataFrame): Indicator-enriched OHLCV data.
            index (int): Index to evaluate.

        Returns:
            bool: True if exit conditions are met, else False.
        """
        row = df.iloc[index]
        prev = df.iloc[index - 1]

        return self.position and (
            row["RSI"] < self.rsi_threshold_exit < prev["RSI"]
            or prev["MACD"] > prev["MACD_SIGNAL"]
            and row["MACD"] < row["MACD_SIGNAL"]
        )
