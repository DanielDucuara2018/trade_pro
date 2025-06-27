import pandas as pd
import pandas_ta as ta

from trade_pro.strategy.base import Base


class MACDStrategy(Base):
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
        return self.macd_fast < self.macd_slow

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """calculates the indicators used in buying and selling"""

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

    def entry_condition(self, df_1h: pd.DataFrame, *, index: int = 0) -> bool:
        row = df_1h.iloc[index]
        prev = df_1h.iloc[index - 1]

        return (
            not self.position
            and row["close"] > row["EMA"]  # Trend filter
            and row["ADX"] > self.adx_treshold  # Trend strength
            and prev["RSI"] < self.rsi_threshold_entry < row["RSI"]  # RSI crossover up
            and prev["MACD"] < prev["MACD_SIGNAL"]
            and row["MACD"] > row["MACD_SIGNAL"]  # MACD crossover
        )

    def exit_condition(self, df_1h: pd.DataFrame, *, index: int = 0) -> bool:
        row = df_1h.iloc[index]
        prev = df_1h.iloc[index - 1]

        return self.position and (
            row["RSI"] < self.rsi_threshold_exit < prev["RSI"]
            or prev["MACD"] > prev["MACD_SIGNAL"]
            and row["MACD"] < row["MACD_SIGNAL"]
        )
