import pandas as pd
import pandas_ta as ta

from trade_pro.strategy.base import Base


class EMAStrategy(Base):
    """
    A trading strategy based on the DEMA (Double Exponential Moving Average)
    and TEMA (Triple Exponential Moving Average) indicators using 1-hour BTC/USDT data.

    Entry Condition:
        - No open position.
        - Price is above DEMA.
        - TEMA_FAST crosses above TEMA_SLOW.

    Exit Condition:
        - Open position exists.
        - Price is still above DEMA.
        - TEMA_FAST crosses below TEMA_SLOW with previous TEMA_FAST above both.

    Parameters:
        symbol (str): Trading pair symbol, e.g. "BTC/USDT".
        initial_balance (float): Starting capital.
        timeframes (list[str]): List of timeframes used (must include "1h").
        start_backtest_index (int): Index to begin backtesting from.
        dema_period (int): Period for the DEMA indicator.
        tema_fast (int): Shorter period for the TEMA indicator (fast line).
        tema_slow (int): Longer period for the TEMA indicator (slow line).
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float,
        timeframes: list[str],
        start_backtest_index: int,
        dema_period: int,
        tema_fast: int,
        tema_slow: int,
    ):
        super().__init__(
            symbol, initial_balance, timeframes, start_backtest_index=start_backtest_index
        )
        self.dema_period = dema_period
        self.tema_fast = tema_fast
        self.tema_slow = tema_slow

    def check_config(self) -> bool:
        """
        Validates that the fast TEMA period is less than the slow TEMA period.

        Returns:
            bool: True if the configuration is valid, False otherwise.
        """
        return self.tema_fast < self.tema_slow

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Computes DEMA, TEMA_FAST, and TEMA_SLOW indicators on 1h timeframe data.

        Args:
            data (dict[str, pd.DataFrame]): Dictionary containing timeframes as keys
                                            and OHLCV data as values.

        Returns:
            pd.DataFrame: 1h DataFrame with added indicator columns.
        """

        # get data
        df_1h = data["1h"]

        df_1h["DEMA"] = ta.dema(df_1h["close"], length=self.dema_period)
        df_1h["TEMA_FAST"] = ta.tema(df_1h["close"], length=self.tema_fast)
        df_1h["TEMA_SLOW"] = ta.tema(df_1h["close"], length=self.tema_slow)

        return df_1h

    def entry_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        """
        Determines if entry conditions are met:
            - No position is open.
            - Price is above DEMA.
            - TEMA_FAST crosses above TEMA_SLOW.

        Args:
            df (pd.DataFrame): DataFrame containing the indicators.
            index (int): Current row index for evaluation.

        Returns:
            bool: True if entry condition is met, False otherwise.
        """

        row = df.iloc[index]
        prev = df.iloc[index - 1]

        return (
            not self.position
            and row["close"] > row["DEMA"]
            and prev["TEMA_FAST"] < prev["TEMA_SLOW"]
            and row["TEMA_FAST"] > row["TEMA_SLOW"]
        )

    def exit_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        """
        Determines if exit conditions are met:
            - A position is open.
            - Price is above DEMA.
            - TEMA_FAST crosses below TEMA_SLOW, and TEMA_SLOW is below previous TEMA_FAST.

        Args:
            df (pd.DataFrame): DataFrame containing the indicators.
            index (int): Current row index for evaluation.

        Returns:
            bool: True if exit condition is met, False otherwise.
        """

        row = df.iloc[index]

        return self.position and (row["TEMA_FAST"] < row["TEMA_SLOW"] or row["close"] < row["DEMA"])
