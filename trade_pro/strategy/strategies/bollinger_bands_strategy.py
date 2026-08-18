import pandas as pd
import pandas_ta as ta

from trade_pro.strategy.strategies.atr_strategy_base import ATRStrategyBase


class BollingerBandsStrategy(ATRStrategyBase):
    """
    Bollinger Bands Mean Reversion trading strategy.

    Entry Condition:
        - Price touches or crosses below lower band (oversold)
        - RSI confirms oversold (optional)

    Exit Condition:
        - Price reaches middle band (mean reversion)
        OR
        - Price touches upper band (maximum target)
        OR
        - Stop loss hit

    Args:
        symbol (str): Trading symbol (e.g., 'BTCUSDT').
        initial_balance (float): Starting account balance.
        timeframes (list[str]): List of timeframes to use.
        start_backtest_index (int): Index to start backtesting from.
        bb_period (int): Bollinger Bands period.
        bb_std (float): Number of standard deviations.
        use_rsi_filter (bool): Require RSI confirmation.
        rsi_period (int): RSI period for filter.
        rsi_threshold (float): RSI threshold for oversold.
        exit_at_middle (bool): Exit at middle band vs upper band.
        atr_period (int): ATR period for stop loss calculation.
        atr_stop_multiplier (float): ATR multiplier for stop distance.
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float,
        timeframes: list[str],
        start_backtest_index: int,
        bb_period: int = 20,
        bb_std: float = 2.0,
        use_rsi_filter: bool = True,
        rsi_period: int = 14,
        rsi_threshold: float = 40,
        exit_at_middle: bool = True,
        atr_period: int = 14,
        atr_stop_multiplier: float = 2.0,
        **kwargs,
    ):
        super().__init__(
            symbol, initial_balance, timeframes, start_backtest_index=start_backtest_index, **kwargs
        )
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.use_rsi_filter = use_rsi_filter
        self.rsi_period = rsi_period
        self.rsi_threshold = rsi_threshold
        self.exit_at_middle = exit_at_middle
        self.atr_period = atr_period
        self.atr_stop_multiplier = atr_stop_multiplier

    def check_config(self) -> bool:
        """Validate configuration parameters"""
        return self.bb_period > 0 and self.bb_std > 0 and self.rsi_period > 0

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Calculate Bollinger Bands, RSI, and ATR"""
        df = data[self.timeframes[0]]

        # Bollinger Bands
        bb = ta.bbands(df["close"], length=self.bb_period, std=self.bb_std)
        df["BB_upper"] = bb[f"BBU_{self.bb_period}_{self.bb_std}"]
        df["BB_middle"] = bb[f"BBM_{self.bb_period}_{self.bb_std}"]
        df["BB_lower"] = bb[f"BBL_{self.bb_period}_{self.bb_std}"]

        # RSI filter
        df["RSI"] = ta.rsi(df["close"], length=self.rsi_period)

        # ATR for stop loss
        df["ATR"] = ta.atr(df["high"], df["low"], df["close"], length=self.atr_period)

        return df

    def entry_condition(self, df: pd.DataFrame, *, index: int = -1) -> bool:
        """Entry when price touches lower Bollinger Band"""
        if self.position:
            return False
        if 0 <= index < 1:
            # Not enough history yet at the very start of a backtest
            return False

        row = df.iloc[index]
        prev = df.iloc[index - 1]

        # Price crosses below lower band (oversold)
        bb_signal = prev["close"] >= prev["BB_lower"] and row["close"] <= row["BB_lower"]

        # RSI filter: confirm oversold
        rsi_ok = not self.use_rsi_filter or row["RSI"] < self.rsi_threshold

        return bb_signal and rsi_ok

    def exit_condition(self, df: pd.DataFrame, *, index: int = -1) -> bool:
        """Exit when price reaches target band"""
        if not self.position:
            return False

        row = df.iloc[index]

        # Exit at middle or upper band
        target_band = row["BB_middle"] if self.exit_at_middle else row["BB_upper"]
        return row["close"] >= target_band

    def _calculate_take_profit(
        self, entry_price: float, stop_loss_price: float, row: pd.Series
    ) -> float:
        """Take profit at target Bollinger Band"""
        return row["BB_middle"] if self.exit_at_middle else row["BB_upper"]

    def _get_trade_metadata(self, row: pd.Series, atr_value: float, entry_price: float) -> dict:
        """Add Bollinger Bands-specific metadata"""
        metadata = super()._get_trade_metadata(row, atr_value, entry_price)
        metadata.update(
            {
                "bb_lower": row["BB_lower"],
                "bb_middle": row["BB_middle"],
                "bb_upper": row["BB_upper"],
                "rsi": row["RSI"],
            }
        )
        return metadata
