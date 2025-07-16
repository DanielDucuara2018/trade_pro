import pandas as pd
import pandas_ta as ta

from trade_pro.strategy.base import Base


class PiCycleStrategy(Base):
    """
    A trend-filtering trading strategy based on the Pi Cycle Top indicator.

    This strategy uses two moving averages on the 1-day timeframe:
        - 111-period SMA
        - 350-period EMA (doubled for Pi Cycle Top)

    Entry Conditions:
        - No current position
        - Pi Cycle Top signal is NOT triggered (SMA_111 < 2 * SMA_350)

    Exit Conditions:
        - Position is open
        - Pi Cycle Top signal is triggered (SMA_111 crosses above 2 * SMA_350)

    Args:
        symbol (str): Trading symbol (e.g., 'BTCUSDT').
        initial_balance (float): Starting account balance.
        timeframes (list[str]): List of timeframes to use (must include '1d').
        start_backtest_index (int): Index to start backtesting from.
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float,
        timeframes: list[str],
        start_backtest_index: int,
        pi_sma_fast: int,
        pi_sma_slow: int,
        ema_fast: int,
        sma_slow: int,
    ):
        super().__init__(
            symbol, initial_balance, timeframes, start_backtest_index=start_backtest_index
        )
        self.pi_sma_fast = pi_sma_fast
        self.pi_sma_slow = pi_sma_slow
        self.ema_fast = ema_fast
        self.sma_slow = sma_slow

    def check_config(self) -> bool:
        """Always returns True (no user-configurable parameters)."""
        return self.pi_sma_fast < self.pi_sma_slow and self.ema_fast < self.sma_slow

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Computes Pi Cycle Top indicators using pandas_ta on daily data.

        Args:
            data (dict[str, pd.DataFrame]): Dictionary of timeframe DataFrames.

        Returns:
            pd.DataFrame: Modified daily DataFrame with Pi Cycle indicator columns.
        """
        df_1d = data["1d"]

        df_1d[f"SMA_{self.pi_sma_fast}"] = ta.sma(df_1d["close"], length=self.pi_sma_fast)
        df_1d[f"SMA_{self.pi_sma_slow}"] = ta.sma(df_1d["close"], length=self.pi_sma_slow)
        df_1d["Pi_Cycle_Top"] = df_1d[f"SMA_{self.pi_sma_slow}"] * 2

        df_1d[f"EMA_{self.ema_fast}"] = ta.ema(df_1d["close"], length=self.ema_fast)
        df_1d[f"SMA_{self.sma_slow}"] = ta.sma(df_1d["close"], length=self.sma_slow)

        return df_1d

    def entry_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        """
        Entry occurs only if the Pi Cycle Top signal is NOT triggered.

        Args:
            df (pd.DataFrame): DataFrame containing indicator values.
            index (int): Index to evaluate (default: current).

        Returns:
            bool: True if entry is allowed (no market top detected).
        """
        row = df.iloc[index]
        prev = df.iloc[index - 1]
        prev_2 = df.iloc[index - 2]

        return (
            not self.position
            and prev_2[f"EMA_{self.ema_fast}"]
            < prev[f"SMA_{self.sma_slow}"]
            < row[f"EMA_{self.ema_fast}"]
        )

    def exit_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        """
        Exits when SMA_111 crosses above 2 * SMA_350 (Pi Cycle Top trigger).

        Args:
            df (pd.DataFrame): Indicator DataFrame.
            index (int): Row index to check.

        Returns:
            bool: True if Pi Cycle Top condition is met.
        """
        row = df.iloc[index]
        prev = df.iloc[index - 1]
        prev_2 = df.iloc[index - 2]

        return (
            self.position
            and prev_2[f"SMA_{self.pi_sma_fast}"]
            < prev["Pi_Cycle_Top"]
            < row[f"SMA_{self.pi_sma_fast}"]
        )
