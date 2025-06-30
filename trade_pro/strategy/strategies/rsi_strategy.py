import pandas as pd
import pandas_ta as ta

from trade_pro.strategy.base import Base


class RSIStrategy(Base):
    """
    A trend-following RSI strategy that enters trades when price is above EMA,
    ADX confirms a strong trend, and RSI crosses above the oversold threshold.
    The position is exited when RSI crosses below the overbought threshold.

    Args:
        symbol (str): Trading symbol (e.g., "BTCUSDT").
        initial_balance (float): Starting account balance.
        timeframes (list[str]): List of timeframes used (must include "1h").
        start_backtest_index (int): Index from which backtesting starts.
        rsi_period (int): RSI indicator lookback period.
        rsi_oversold (int): RSI value indicating oversold threshold for entry.
        rsi_overbought (int): RSI value indicating overbought threshold for exit.
        ema_period (int): EMA period used as a trend filter.
        adx_period (int): ADX period used to confirm trend strength.
        adx_treshold (int): ADX value above which trend strength is considered valid.
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float,
        timeframes: list[str],
        start_backtest_index: int,
        rsi_period: int,
        rsi_oversold: int,
        rsi_overbought: int,
        ema_period: int,
        adx_period: int,
        adx_treshold: int,
    ):
        super().__init__(
            symbol, initial_balance, timeframes, start_backtest_index=start_backtest_index
        )
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.ema_period = ema_period
        self.adx_period = adx_period
        self.adx_treshold = adx_treshold

    def check_config(self) -> bool:
        """
        Validate strategy parameters.

        Returns:
            bool: True if RSI thresholds are within [0, 100] and oversold < overbought.
        """
        return (
            0 <= self.rsi_oversold <= 100
            and 0 <= self.rsi_overbought <= 100
            and self.rsi_oversold < self.rsi_overbought
        )

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Compute required technical indicators on the provided price data.

        Args:
            data (dict[str, pd.DataFrame]): Dictionary of dataframes keyed by timeframe.

        Returns:
            pd.DataFrame: DataFrame with added columns: RSI, EMA, and ADX.
        """
        df_1h = data["1h"]

        df_1h["RSI"] = ta.rsi(df_1h["close"], length=self.rsi_period)
        df_1h["EMA"] = ta.ema(df_1h["close"], length=self.ema_period)
        df_1h["ADX"] = ta.adx(df_1h["high"], df_1h["low"], df_1h["close"], length=self.adx_period)[
            f"ADX_{self.adx_period}"
        ]

        return df_1h

    def entry_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        """
        Determine whether entry condition is met at the given index.

        Entry is signaled when:
            - No open position
            - Price is above EMA (trend filter)
            - ADX indicates trend strength
            - RSI crosses above the oversold threshold

        Args:
            df (pd.DataFrame): DataFrame with indicators computed.
            index (int): Index to evaluate the entry condition.

        Returns:
            bool: True if entry condition is met.
        """
        row = df.iloc[index]
        prev = df.iloc[index - 1]

        return (
            not self.position
            and row["close"] > row["EMA"]
            and row["ADX"] > self.adx_treshold
            and prev["RSI"] < self.rsi_oversold < row["RSI"]
        )

    def exit_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        """
        Determine whether exit condition is met at the given index.

        Exit is signaled when:
            - Position is open
            - Price is above EMA (trend continues)
            - RSI crosses below the overbought threshold (momentum weakening)

        Args:
            df (pd.DataFrame): DataFrame with indicators computed.
            index (int): Index to evaluate the exit condition.

        Returns:
            bool: True if exit condition is met.
        """
        row = df.iloc[index]
        prev = df.iloc[index - 1]

        return self.position and prev["RSI"] > self.rsi_overbought > row["RSI"]
