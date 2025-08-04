import pandas as pd
import pandas_ta as ta

from trade_pro.strategy.base import Base


class EmaAtrReversalStrategy(Base):
    """
    Estrategia basada en:
    - Tendencia positiva vía EMA 40
    - Patrón de reversión (inside bar)
    - Gestión de riesgo vía ATR 21

    Condición de entrada:
        - Precio actual por encima de EMA 40
        - El máximo de hace 2 velas > máximo de hace 1 vela
        - El mínimo de hace 2 velas < mínimo de hace 1 vela
        - Si se cumplen, comprar a la apertura de la siguiente vela
        - SL = entrada - 2 * ATR
        - TP = entrada + 2 * ATR
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float,
        timeframes: list[str],
        start_backtest_index: int,
        ema_period: int,
        atr_period: int,
        atr_multiplier: float,
    ):
        super().__init__(
            symbol, initial_balance, timeframes, start_backtest_index=start_backtest_index
        )
        self.ema_period = ema_period
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier

        self.stop_loss: float = 0.0
        self.take_profit: float = 0.0

    def check_config(self) -> bool:
        """
        Validates that the fast TEMA period is less than the slow TEMA period.

        Returns:
            bool: True if the configuration is valid, False otherwise.
        """
        return True

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        df = data[self.timeframes[0]]
        df[f"EMA_{self.ema_period}"] = ta.ema(df["close"], length=self.ema_period)
        df[f"ATR_{self.atr_period}"] = ta.atr(
            df["high"], df["low"], df["close"], length=self.atr_period
        )
        return df

    def entry_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        next_candle = df.iloc[index]
        row = df.iloc[index - 1]
        prev = df.iloc[index - 2]
        prev2 = df.iloc[index - 3]

        condition = (
            not self.position
            and row["close"] > row[f"EMA_{self.ema_period}"]
            and prev2["high"] > prev["high"]
            and prev2["low"] < prev["low"]
        )

        if condition:
            atr = next_candle[f"ATR_{self.atr_period}"]
            entry_price = next_candle["open"]
            self.stop_loss = entry_price - self.atr_multiplier * atr
            self.take_profit = entry_price + self.atr_multiplier * atr

        return condition

    def exit_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        row = df.iloc[index]

        condition = self.position and (
            row["close"] <= self.stop_loss or row["close"] >= self.take_profit
        )

        if condition:
            self.stop_loss = 0.0
            self.take_profit = 0.0

        return condition
