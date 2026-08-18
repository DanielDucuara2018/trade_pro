import pandas as pd

from trade_pro.strategy.base import Base


class ATRStrategyBase(Base):
    """
    Base class for strategies using ATR-based stops and risk management.

    Provides common execute_entry logic with:
    - ATR-based stop loss calculation
    - Risk/reward validation
    - Automatic stop and take profit setting
    - Metadata tracking

    Subclasses must implement:
    - check_config()
    - compute_indicators()
    - entry_condition()
    - exit_condition()

    Subclasses can optionally override:
    - _calculate_take_profit() - Custom TP logic (default: R:R ratio-based)
    - _get_trade_metadata() - Add strategy-specific metadata
    - _should_use_atr_stops() - Control when ATR stops are used (default: always)
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float,
        timeframes: list[str],
        start_backtest_index: int,
        atr_period: int = 14,
        atr_stop_multiplier: float = 2.0,
        risk_reward_ratio: float = 2.5,
        use_atr_stops: bool = True,
        **kwargs,
    ):
        super().__init__(
            symbol, initial_balance, timeframes, start_backtest_index=start_backtest_index, **kwargs
        )
        self.atr_period = atr_period
        self.atr_stop_multiplier = atr_stop_multiplier
        self.risk_reward_ratio = risk_reward_ratio
        self.use_atr_stops = use_atr_stops

    def _should_use_atr_stops(self) -> bool:
        """
        Determine if ATR stops should be used for this entry.
        Override in subclass for custom logic.

        Returns:
            True if ATR stops should be used, False otherwise
        """
        return self.use_atr_stops

    def _calculate_atr_stop_loss(
        self, row: pd.Series, next_row: pd.Series | None, atr_value: float
    ) -> float:
        """
        Calculate stop loss price based on ATR.

        Args:
            row: Current candle data with indicators
            next_row: Next candle data (if using next candle open)
            atr_value: ATR value from indicators

        Returns:
            Stop loss price (0 if ATR stops not enabled or ATR invalid)
        """
        if not self._should_use_atr_stops() or atr_value <= 0:
            return 0

        execution_price = self._get_execution_price(row, next_row)
        entry_price_estimate = self._calculate_entry_price(execution_price)
        return entry_price_estimate - (atr_value * self.atr_stop_multiplier)

    def _validate_entry_risk_reward(
        self,
        row: pd.Series,
        next_row: pd.Series | None,
        atr_value: float,
        stop_loss_price: float,
    ) -> bool:
        """
        Validate trade meets minimum risk/reward ratio.

        Args:
            row: Current candle data with indicators
            next_row: Next candle data (if using next candle open)
            atr_value: ATR value from indicators
            stop_loss_price: Calculated stop loss price

        Returns:
            True if validation passes or not required, False to skip trade
        """
        if not self._should_use_atr_stops() or atr_value <= 0:
            return True

        if not self.risk_manager.use_risk_management:
            return True

        execution_price = self._get_execution_price(row, next_row)
        entry_price_estimate = self._calculate_entry_price(execution_price)
        take_profit_price = self._calculate_take_profit(entry_price_estimate, stop_loss_price, row)

        return self._validate_trade_risk_reward(
            entry_price_estimate, stop_loss_price, take_profit_price
        )

    def _set_trade_stops_and_metadata(
        self, entry_price: float, atr_value: float, row: pd.Series
    ) -> None:
        """
        Set stop loss, take profit, and metadata on current trade.

        Args:
            entry_price: Actual entry price
            atr_value: ATR value used for stops
            row: Current candle data with indicators
        """
        if (
            not self._should_use_atr_stops()
            or atr_value <= 0
            or not hasattr(self, "_current_single_trade")
            or not self._current_single_trade
        ):
            return

        trade = self._current_single_trade

        # Set stop loss and take profit
        trade.stop_loss = entry_price - (atr_value * self.atr_stop_multiplier)
        trade.take_profit = self._calculate_take_profit(entry_price, trade.stop_loss, row)
        trade.metadata = self._get_trade_metadata(row, atr_value, entry_price)

    def _calculate_take_profit(
        self, entry_price: float, stop_loss_price: float, row: pd.Series
    ) -> float:
        """
        Calculate take profit price. Override in subclass for custom logic.

        Args:
            entry_price: Calculated entry price
            stop_loss_price: Calculated stop loss price
            row: Current candle data with indicators

        Returns:
            Take profit price
        """
        stop_distance = entry_price - stop_loss_price
        return entry_price + (stop_distance * self.risk_reward_ratio)

    def _get_trade_metadata(self, row: pd.Series, atr_value: float, entry_price: float) -> dict:
        """
        Get metadata for trade. Override in subclass to add custom fields.

        Args:
            row: Current candle data with indicators
            atr_value: ATR value used for stops
            entry_price: Actual entry price

        Returns:
            Dictionary of metadata fields
        """
        stop_distance = atr_value * self.atr_stop_multiplier
        return {
            "atr": atr_value,
            "stop_distance": stop_distance,
            "target_distance": stop_distance * self.risk_reward_ratio,
            "risk_per_trade_pct": self.risk_manager.risk_per_trade_pct
            if self.risk_manager.use_risk_management
            else None,
        }

    def execute_entry(self, row: pd.Series, next_row: pd.Series | None = None):
        """Execute entry with ATR-based stops and risk management"""
        atr_value = row.get("ATR", 0)
        stop_loss_price = self._calculate_atr_stop_loss(row, next_row, atr_value)

        # Validate R:R ratio before entry if using risk management
        if not self._validate_entry_risk_reward(row, next_row, atr_value, stop_loss_price):
            return self._init_single_position_vars()

        # Execute entry with calculated stop loss for risk-based sizing
        entry_price, entry_time, units = super().execute_entry(
            row, next_row, stop_loss=stop_loss_price
        )

        # Set stops and metadata on created trade
        self._set_trade_stops_and_metadata(entry_price, atr_value, row)

        return entry_price, entry_time, units
