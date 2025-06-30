import pandas as pd

from trade_pro.strategy.strategies.mas_strategy import MASStrategy


class VolumeMASStrategy(MASStrategy):
    """
    A volume-enhanced version of the Moving Average Spread (MAS) strategy.

    This strategy inherits all the conditions of MASStrategy, with an additional
    volume filter: a trade is only entered if the current volume is above its
    moving average (volume MA), indicating stronger market participation.

    Entry Conditions:
        - All conditions from MASStrategy are met.
        - Current volume > volume moving average.

    Exit Conditions:
        - Same as MASStrategy (based on MAS crossover down).

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
        volume_ma_period (float): Period for volume moving average filter.
    """

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
        volume_ma_period: float,
    ):
        super().__init__(
            symbol,
            initial_balance,
            timeframes,
            start_backtest_index,
            fast,
            slow,
            rsi_period,
            rsi_threshold,
            macd_fast,
            macd_slow,
            macd_signal,
            trend_sma_period,
        )
        self.volume_ma_period = volume_ma_period

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Computes all technical indicators including volume-based filters.

        Adds:
            - Volume moving average (VOLUME_MA)

        Args:
            data (dict[str, pd.DataFrame]): Dictionary of OHLCV data for timeframes "1h" and "1d".

        Returns:
            pd.DataFrame: 1h DataFrame with added indicator columns.
        """
        # get data
        df_1h = super().compute_indicators(data)

        # --- Volume MA ---
        df_1h["VOLUME_MA"] = df_1h["volume"].rolling(self.volume_ma_period).mean()

        return df_1h

    def entry_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        """
        Determines whether to enter a position.

        Additional condition:
            - Volume must be above its moving average.

        Args:
            df (pd.DataFrame): 1h OHLCV + indicator DataFrame.
            index (int): Row index to evaluate.

        Returns:
            bool: True if entry conditions (including volume filter) are met.
        """
        row = df.iloc[index]

        return super().entry_condition(df, index=index) and row["volume"] > row["VOLUME_MA"]
