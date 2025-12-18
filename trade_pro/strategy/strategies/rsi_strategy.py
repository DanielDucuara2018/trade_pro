import pandas as pd
import pandas_ta as ta

from trade_pro.strategy.strategies.atr_strategy_base import ATRStrategyBase


class RSIStrategy(ATRStrategyBase):
    """
    RSI-based trading strategy with trend filter.

    Entry Condition:
        - RSI crosses above oversold level (default 30)
        - Price above 200-period MA (optional trend filter)

    Exit Condition:
        - RSI crosses below overbought level (default 70)
        OR
        - Stop loss / Take profit hit

    Args:
        symbol (str): Trading symbol (e.g., 'BTCUSDT').
        initial_balance (float): Starting account balance.
        timeframes (list[str]): List of timeframes to use.
        start_backtest_index (int): Index to start backtesting from.
        rsi_period (int): RSI calculation period.
        rsi_oversold (float): Oversold threshold for entry.
        rsi_overbought (float): Overbought threshold for exit.
        use_trend_filter (bool): Require price above MA for entry.
        trend_ma_period (int): MA period for trend filter.
        atr_period (int): ATR period for stop loss calculation.
        atr_stop_multiplier (float): ATR multiplier for stop distance.
        risk_reward_ratio (float): Risk/reward ratio for take profit.
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float,
        timeframes: list[str],
        start_backtest_index: int,
        rsi_period: int = 14,
        rsi_oversold: float = 30,
        rsi_overbought: float = 70,
        use_trend_filter: bool = True,
        trend_ma_period: int = 200,
        atr_period: int = 14,
        atr_stop_multiplier: float = 2.0,
        risk_reward_ratio: float = 2.5,
        **kwargs,
    ):
        super().__init__(
            symbol, initial_balance, timeframes, start_backtest_index=start_backtest_index, **kwargs
        )
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.use_trend_filter = use_trend_filter
        self.trend_ma_period = trend_ma_period
        self.atr_period = atr_period
        self.atr_stop_multiplier = atr_stop_multiplier
        self.risk_reward_ratio = risk_reward_ratio

    def check_config(self) -> bool:
        """Validate configuration parameters"""
        return (
            0 < self.rsi_oversold < self.rsi_overbought < 100
            and self.rsi_period > 0
            and self.trend_ma_period > 0
        )

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Calculate RSI, MA trend filter, and ATR"""
        df = data[self.timeframes[0]]

        # RSI
        df["RSI"] = ta.rsi(df["close"], length=self.rsi_period)

        # Trend filter MA
        df["MA_trend"] = ta.sma(df["close"], length=self.trend_ma_period)

        # ATR for stop loss
        df["ATR"] = ta.atr(df["high"], df["low"], df["close"], length=self.atr_period)

        return df

    def entry_condition(self, df: pd.DataFrame, *, index: int = -1) -> bool:
        """Entry when RSI crosses above oversold"""
        if self.position:
            return False

        row = df.iloc[index]
        prev = df.iloc[index - 1]

        # RSI crosses above oversold
        rsi_signal = prev["RSI"] <= self.rsi_oversold and row["RSI"] > self.rsi_oversold

        # Trend filter: price above MA
        trend_ok = not self.use_trend_filter or row["close"] > row["MA_trend"]

        return rsi_signal and trend_ok

    def exit_condition(self, df: pd.DataFrame, *, index: int = -1) -> bool:
        """Exit when RSI crosses below overbought"""
        if not self.position:
            return False

        row = df.iloc[index]
        prev = df.iloc[index - 1]

        # RSI crosses below overbought
        return prev["RSI"] >= self.rsi_overbought and row["RSI"] < self.rsi_overbought

    def _get_trade_metadata(self, row: pd.Series, atr_value: float, entry_price: float) -> dict:
        """Add RSI-specific metadata"""
        metadata = super()._get_trade_metadata(row, atr_value, entry_price)
        metadata["rsi"] = row["RSI"]
        return metadata
