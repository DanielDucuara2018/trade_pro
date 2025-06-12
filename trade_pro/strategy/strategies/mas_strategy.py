import numpy as np
import pandas as pd
import pandas_ta as ta

from trade_pro.strategy.base import Base


class MASStrategy(Base):
    def __init__(
        self,
        symbol: str,
        initial_balance: float,
        timeframes: list[str],
        start_backtest_index: int,
        fast: float,
        slow: float,
        rsi_period: float,
        rsi_threshold: float,
        macd_fast: float,
        macd_slow: float,
        macd_signal: float,
        trend_sma_period: float,
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

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """calculates the indicators used in buying and selling"""

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
        df_1h["BULLISH_TREND"] = df_1d["BULLISH_TREND"].reindex(df_1h.index, method="ffill")

        return df_1h

    def entry_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        """Buy when the price is higher than the dema indicator and the fast tema
        crosses the slow tema upwards."""

        row = df.iloc[index]
        prev = df.iloc[index - 1]
        prev2 = df.iloc[index - 2]

        return (
            not self.position
            and prev2["SPREAD_SIGN"] == -1
            and prev["SPREAD_SIGN"] == -1
            and row["SPREAD_SIGN"] == 1
            and row["RSI"] < self.rsi_threshold
            and row["MACD"] > row["MACD_SIGNAL"]
            and row["BULLISH_TREND"]
        )

    def exit_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        """Sell when the price is higher than the dema indicator and the fast tema
        crosses the slow tema downwards"""
        row = df.iloc[index]
        prev = df.iloc[index - 1]
        prev2 = df.iloc[index - 2]

        return self.position and (
            prev2["SPREAD_SIGN"] == 1 and prev["SPREAD_SIGN"] == 1 and row["SPREAD_SIGN"] == -1
        )
