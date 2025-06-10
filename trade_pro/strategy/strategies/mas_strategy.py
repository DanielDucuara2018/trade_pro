import pandas as pd
import pandas_ta as ta
import numpy as np
from trade_pro.strategy.base import Base


class MASStrategy(Base):
    def __init__(
        self,
        fast,
        slow,
        rsi_period,
        macd_fast,
        macd_slow,
        macd_signal,
        trend_sma_period,
        volume_ma_period,
    ):
        self.fast = fast
        self.slow = slow
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.trend_sma_period = trend_sma_period
        self.volume_ma_period = volume_ma_period

    def indicators(self, df: pd.DataFrame, *, df_high: pd.DataFrame | None = None) -> pd.Dataframe:
        """calculates the indicators used in buying and selling"""

        # --- Moving Average Spread ---
        df["FAST"] = ta.sma(df["close"], length=self.fast)
        df["SLOW"] = ta.sma(df["close"], length=self.slow)
        df["SPREAD"] = df["FAST"] - df["SLOW"]
        df["SPREAD_SIGN"] = np.where(df["SPREAD"] > 0, 1, -1)

        # --- RSI ---
        df["RSI"] = ta.rsi(df["close"], length=self.rsi_period)

        # --- MACD ---
        macd = ta.macd(df["close"], self.macd_fast,self.macd_slow, self.macd_signal)
        df["MACD"], df["MACD_SIGNAL"] = (
            macd[f"MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"],
            macd[f"MACDs_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"],
        )

        # --- Volume MA ---
        df["VOLUME_MA"] = df["volume"].rolling(self.volume_ma_period).mean()

        # --- Daily SMA Trend Filter ---
        df_high[f"SMA{self.trend_sma_period}"] = ta.sma(df_high["close"], self.trend_sma_period)
        df_high["BULLISH_TREND"] = df_high["close"] > df_high[f"SMA{self.trend_sma_period}"]
        df["BULLISH_TREND"] = df_high["BULLISH_TREND"].reindex(df.index, method="ffill")
        
        return df

    def entry_condition(self, df: pd.DataFrame,  *, index: int = 0) -> bool:
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
            and row["volume"] > row["VOLUME_MA"]
        )

    def exit_condition(self, df: pd.DataFrame,  *, index: int = 0) -> bool:
        """Sell when the price is higher than the dema indicator and the fast tema
        crosses the slow tema downwards"""
        row = df.iloc[index]
        prev = df.iloc[index - 1]
        prev2 = df.iloc[index - 2]

        return self.position and (
            prev2["SPREAD_SIGN"] == 1 and prev["SPREAD_SIGN"] == 1 and row["SPREAD_SIGN"] == -1
        )
