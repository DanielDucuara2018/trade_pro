import pandas as pd
import pandas_ta as ta

from trade_pro.strategy.base import Base


# TODO check if adding a trend following indicator would be necessary
class StochasticStrategy(Base):
    """
    A trading strategy based on Stochastic Oscillator and RSI indicators.

    Entry Conditions:
        - No current position
        - Stochastic K is below the oversold threshold
        - Stochastic K crosses above Stochastic D (bullish crossover)
        - RSI crosses above the RSI oversold level

    Exit Conditions:
        - Position is open
        - Stochastic K is above the overbought threshold
        - Stochastic K crosses below Stochastic D (bearish crossover)
        - RSI crosses below the RSI overbought level

    Args:
        symbol (str): Trading symbol (e.g., 'BTCUSDT').
        initial_balance (float): Starting account balance.
        timeframes (list[str]): List of timeframes to use (expects '1h' in this version).
        start_backtest_index (int): Index to start backtesting from.
        rsi_period (int): Period for RSI calculation.
        rsi_oversold (int): RSI value considered oversold.
        # rsi_overbought (int): RSI value considered overbought.
        stoch_k_period (int): %K period for Stochastic Oscillator.
        stoch_d_period (int): %D period for Stochastic Oscillator.
        stoch_oversold (int): Threshold for oversold in Stochastic.
        stoch_overbought (int): Threshold for overbought in Stochastic.
        stoch_smooth_period (int): Smoothing period for Stochastic %K.
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float,
        timeframes: list[str],
        start_backtest_index: int,
        rsi_period: int,
        rsi_oversold: int,
        stoch_k_period: int,
        stoch_d_period: int,
        stoch_oversold: int,
        stoch_overbought: int,
        stoch_smooth_period: int,
    ):
        super().__init__(
            symbol, initial_balance, timeframes, start_backtest_index=start_backtest_index
        )
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.stoch_k_period = stoch_k_period
        self.stoch_d_period = stoch_d_period
        self.stoch_oversold = stoch_oversold
        self.stoch_overbought = stoch_overbought
        self.stoch_smooth_period = stoch_smooth_period

    def check_config(self) -> bool:
        """
        Validates the configuration values.

        Returns:
            bool: True if all thresholds are within [0, 100], else False.
        """
        return (
            0 <= self.rsi_oversold <= 100
            and 0 <= self.stoch_oversold <= 100
            and 0 <= self.stoch_overbought <= 100
        )

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Computes RSI and Stochastic indicators on 1-hour data.

        Args:
            data (dict[str, pd.DataFrame]): Dictionary of timeframes mapped to DataFrames.

        Returns:
            pd.DataFrame: DataFrame with RSI, STOCH_K, and STOCH_D added.
        """
        df_1h = data["1h"]

        df_1h["RSI"] = ta.rsi(df_1h["close"], length=self.rsi_period)

        stoch = ta.stoch(
            df_1h["high"],
            df_1h["low"],
            df_1h["close"],
            k=self.stoch_k_period,
            d=self.stoch_d_period,
            smooth_k=self.stoch_smooth_period,
        )

        k_col = f"STOCHk_{self.stoch_k_period}_{self.stoch_d_period}_{self.stoch_smooth_period}"
        d_col = f"STOCHd_{self.stoch_k_period}_{self.stoch_d_period}_{self.stoch_smooth_period}"

        df_1h["STOCH_K"] = stoch[k_col]
        df_1h["STOCH_D"] = stoch[d_col]

        return df_1h

    def entry_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        """
        Determines if entry conditions are met.

        Args:
            df (pd.DataFrame): DataFrame containing indicator values.
            index (int): Index to evaluate conditions at (default: current).

        Returns:
            bool: True if all entry conditions are met, else False.
        """
        row = df.iloc[index]
        prev = df.iloc[index - 1]

        return not self.position and (
            (
                row["STOCH_K"] < self.stoch_oversold
                and prev["STOCH_K"] < prev["STOCH_D"]
                and row["STOCH_K"] > row["STOCH_D"]
            )
            or prev["RSI"] < self.rsi_oversold < row["RSI"]
        )

    def exit_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        """
        Determines if exit conditions are met.

        Args:
            df (pd.DataFrame): DataFrame containing indicator values.
            index (int): Index to evaluate conditions at (default: current).

        Returns:
            bool: True if all exit conditions are met, else False.
        """
        row = df.iloc[index]
        prev = df.iloc[index - 1]

        return (
            self.position
            and row["STOCH_K"] > self.stoch_overbought
            and prev["STOCH_K"] > prev["STOCH_D"]
            and row["STOCH_K"] < row["STOCH_D"]
        )
