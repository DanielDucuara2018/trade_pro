from typing import Dict

import pandas as pd
import pandas_ta as ta

from trade_pro.strategy.base import Base, Trade


class MultiEmaStrategy(Base):
    """
    Example strategy demonstrating multiple concurrent positions.

    This strategy:
    - Uses multiple EMA periods to create different entry signals
    - Allows up to 3 concurrent positions
    - Each position uses 25% of available balance
    - Has individual stop-loss and take-profit for each trade

    Entry conditions:
    - Fast EMA crosses above Medium EMA (EMA8 > EMA21)
    - Medium EMA crosses above Slow EMA (EMA21 > EMA55)
    - Price is above all EMAs

    Exit conditions:
    - Stop Loss: Entry price - 2 * ATR
    - Take Profit: Entry price + 3 * ATR
    - Or when Fast EMA crosses below Medium EMA
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float,
        timeframes: list[str],
        start_backtest_index: int,
        fast_ema: int = 8,
        medium_ema: int = 21,
        slow_ema: int = 55,
        atr_period: int = 14,
        atr_multiplier_sl: float = 2.0,
        atr_multiplier_tp: float = 3.0,
        enable_multiple_positions: bool = True,
        max_positions: int = 3,
        position_size_pct: float = 0.25,
        **kwargs,
    ):
        super().__init__(
            symbol,
            initial_balance,
            timeframes,
            start_backtest_index=start_backtest_index,
            allow_multiple_positions=enable_multiple_positions,
            max_concurrent_trades=max_positions,
            position_size_pct=position_size_pct,
            **kwargs,
        )
        self.fast_ema = fast_ema
        self.medium_ema = medium_ema
        self.slow_ema = slow_ema
        self.atr_period = atr_period
        self.atr_multiplier_sl = atr_multiplier_sl
        self.atr_multiplier_tp = atr_multiplier_tp

        # For single position mode compatibility
        self.stop_loss: float = 0.0
        self.take_profit: float = 0.0

    def check_config(self) -> bool:
        """Validate strategy configuration"""
        return (
            self.fast_ema < self.medium_ema < self.slow_ema
            and self.atr_period > 0
            and self.atr_multiplier_sl > 0
            and self.atr_multiplier_tp > 0
        )

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Compute all necessary indicators"""
        df = data[self.timeframes[0]].copy()

        # EMAs
        df[f"EMA_{self.fast_ema}"] = ta.ema(df["close"], length=self.fast_ema)
        df[f"EMA_{self.medium_ema}"] = ta.ema(df["close"], length=self.medium_ema)
        df[f"EMA_{self.slow_ema}"] = ta.ema(df["close"], length=self.slow_ema)

        # ATR for position sizing and stops
        df[f"ATR_{self.atr_period}"] = ta.atr(
            df["high"], df["low"], df["close"], length=self.atr_period
        )

        # EMA cross signals
        df["ema_fast_above_medium"] = df[f"EMA_{self.fast_ema}"] > df[f"EMA_{self.medium_ema}"]
        df["ema_medium_above_slow"] = df[f"EMA_{self.medium_ema}"] > df[f"EMA_{self.slow_ema}"]
        df["price_above_all_emas"] = (
            (df["close"] > df[f"EMA_{self.fast_ema}"])
            & (df["close"] > df[f"EMA_{self.medium_ema}"])
            & (df["close"] > df[f"EMA_{self.slow_ema}"])
        )

        return df

    def entry_condition(self, df: pd.DataFrame, *, index: int = -1) -> bool:
        """
        Entry condition for both single and multiple position modes.

        Looks for:
        1. Fast EMA crossing above Medium EMA
        2. Medium EMA above Slow EMA
        3. Price above all EMAs
        """
        if index < 1:  # Need at least 2 candles for cross detection
            return False

        current = df.iloc[index]
        previous = df.iloc[index - 1]

        # Fast EMA just crossed above Medium EMA
        fast_cross = current["ema_fast_above_medium"] and not previous["ema_fast_above_medium"]

        # Other bullish conditions
        medium_above_slow = current["ema_medium_above_slow"]
        price_above_all = current["price_above_all_emas"]

        entry_signal = fast_cross and medium_above_slow and price_above_all

        if not entry_signal:
            return False

        if not self.allow_multiple_positions:
            if self.position:
                # Don't open a second trade on top of an already-open one.
                return False
            # For single position mode, set stop loss and take profit
            atr = current[f"ATR_{self.atr_period}"]
            entry_price = current["close"]
            self.stop_loss = entry_price - self.atr_multiplier_sl * atr
            self.take_profit = entry_price + self.atr_multiplier_tp * atr

        return True

    def exit_condition(self, df: pd.DataFrame, *, index: int = -1) -> bool:
        """
        Exit condition for single position mode.

        Exits when:
        1. Stop loss or take profit hit
        2. Fast EMA crosses below Medium EMA
        """
        if not self.position:
            return False

        current = df.iloc[index]

        # Price-based exits
        if self.stop_loss > 0 and current["close"] <= self.stop_loss:
            return True
        if self.take_profit > 0 and current["close"] >= self.take_profit:
            return True

        # Technical exit: Fast EMA crosses below Medium EMA
        if index >= 1:
            previous = df.iloc[index - 1]
            fast_cross_down = (
                not current["ema_fast_above_medium"] and previous["ema_fast_above_medium"]
            )
            if fast_cross_down:
                return True

        return False

    def should_exit_position(
        self, trade: Trade, df: pd.DataFrame, *, index: int = -1
    ) -> tuple[bool, float | None, str]:
        """
        Custom exit logic for individual trades in multiple position mode.

        Each trade has its own stop loss and take profit levels.
        """
        if not self.allow_multiple_positions:
            return super().should_exit_position(trade, df, index=index)

        current = df.iloc[index]
        current_price = current["close"]

        # Check stop loss and take profit (set when trade was opened)
        if trade.stop_loss > 0 and current_price <= trade.stop_loss:
            return True, trade.stop_loss, "Stop Loss"
        if trade.take_profit > 0 and current_price >= trade.take_profit:
            return True, trade.take_profit, "Take Profit"

        # Technical exit: Fast EMA crosses below Medium EMA
        if index >= 1:
            previous = df.iloc[index - 1]
            fast_cross_down = (
                not current["ema_fast_above_medium"] and previous["ema_fast_above_medium"]
            )
            if fast_cross_down:
                return True, None, "Exit Signal"

        return False, None, ""

    def _calculate_multi_entry_stop_loss(
        self, row: pd.Series, next_row: pd.Series | None = None
    ) -> float:
        """ATR-based stop-loss, computed *before* entry so risk-based position
        sizing (when use_risk_management is on) actually sizes against it."""
        atr = row[f"ATR_{self.atr_period}"]
        execution_price = self._get_execution_price(row, next_row)
        entry_price_estimate = self._calculate_entry_price(execution_price)
        return entry_price_estimate - self.atr_multiplier_sl * atr

    def _execute_multiple_entry(
        self, row: pd.Series, next_row: pd.Series | None = None, stop_loss: float = 0
    ) -> Trade:
        """
        Override to set take-profit and metadata for each trade. stop_loss is
        already computed (via _calculate_multi_entry_stop_loss) and attached by
        the base implementation before sizing happens.
        """
        trade = super()._execute_multiple_entry(row, next_row, stop_loss)

        if trade.units <= 0:
            # Base already logged and skipped storing this trade (insufficient balance).
            return trade

        atr = row[f"ATR_{self.atr_period}"]
        trade.take_profit = trade.entry_price + self.atr_multiplier_tp * atr

        # Store strategy-specific metadata
        trade.metadata.update(
            {
                "atr_at_entry": atr,
                "fast_ema": row[f"EMA_{self.fast_ema}"],
                "medium_ema": row[f"EMA_{self.medium_ema}"],
                "slow_ema": row[f"EMA_{self.slow_ema}"],
            }
        )

        return trade

    def get_strategy_info(self) -> Dict:
        """Get strategy-specific information for monitoring"""
        info = {
            "strategy_name": "Multi EMA Strategy",
            "parameters": {
                "fast_ema": self.fast_ema,
                "medium_ema": self.medium_ema,
                "slow_ema": self.slow_ema,
                "atr_period": self.atr_period,
                "atr_multiplier_sl": self.atr_multiplier_sl,
                "atr_multiplier_tp": self.atr_multiplier_tp,
            },
            "multiple_positions_enabled": self.allow_multiple_positions,
            "max_concurrent_trades": self.max_concurrent_trades,
            "position_size_pct": self.position_size_pct,
        }

        if self.allow_multiple_positions:
            info["active_trades"] = self.get_active_trades_summary()

        return info
