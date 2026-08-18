import logging
import os
from abc import abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np
import pandas as pd

from trade_pro.strategy.risk_manager import RiskManager
from trade_pro.strategy.utils import (
    fetch_candles,
    get_data,
    plot_equity_curve,
    plot_price_chart,
    update_data,
    wait_for_next_candle,
)
from trade_pro.telegram.runner import TelegramBot

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Represents a trade position (both active and completed)"""

    id: str
    entry_time: pd.Timestamp
    entry_price: float
    units: float
    position_size: float
    stop_loss: float = 0.0
    take_profit: float = 0.0
    metadata: dict = field(default_factory=dict)  # For strategy-specific data

    # Trade completion data (set when trade is closed)
    exit_time: pd.Timestamp | None = None
    exit_price: float | None = None
    pnl: float | None = None
    return_pct: float | None = None
    old_balance: float | None = None
    new_balance: float | None = None
    reason: str | None = None

    @property
    def current_value(self) -> float:
        """Calculate current trade value (for monitoring purposes)"""
        return self.units * self.entry_price

    @property
    def is_closed(self) -> bool:
        """Check if the trade has been closed"""
        return self.exit_time is not None

    @property
    def is_profitable(self) -> bool:
        """Check if the trade is profitable (only valid for closed trades)"""
        return self.pnl is not None and self.pnl > 0

    def close_trade(
        self, exit_time: pd.Timestamp, exit_price: float, old_balance: float, reason: str = ""
    ) -> None:
        """Close the trade and calculate final metrics"""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.pnl = (exit_price - self.entry_price) * self.units
        self.return_pct = self.pnl / self.position_size
        self.old_balance = old_balance
        self.new_balance = old_balance + self.pnl
        self.reason = reason


class Mode(StrEnum):
    BACKTEST = "backtest"
    LIVE = "live"
    OPTIMIZATION = "optimization"


class Base:
    """_summary_

    Raises:
        Exception: _description_

    Returns:
        _type_: _description_
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float,
        timeframes: list[str],
        *,
        position: bool = False,
        commission: float = 0.0004,
        slippage: float = 0.0005,
        start_backtest_index: int = 0,
        start_live_index: int = -2,
        allow_multiple_positions: bool = False,
        max_concurrent_trades: int = 3,
        position_size_pct: float = 1.0,
        use_next_candle_open: bool = False,  # Fix look-ahead bias
        walk_forward_enabled: bool = False,
        walk_forward_train_size: int = 365,  # Days for training
        walk_forward_test_size: int = 90,  # Days for testing
        walk_forward_step: int = 90,  # Days to move forward each iteration
        # Risk Management (Phase 6)
        use_risk_management: bool = False,
        risk_per_trade_pct: float = 0.02,  # 2% of capital at risk per trade
        max_daily_loss_pct: float = 0.05,  # 5% max daily loss
        max_drawdown_pct: float = 0.20,  # 20% max drawdown from peak
        min_risk_reward_ratio: float = 1.5,  # Minimum R:R for trade entry
    ):
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.position = position  # Keep for backward compatibility
        self.timeframes = timeframes
        self.commission = commission
        self.slippage = slippage
        self.start_backtest_index = start_backtest_index
        self.start_live_index = start_live_index
        self.use_next_candle_open = use_next_candle_open

        # Walk-forward testing parameters
        self.walk_forward_enabled = walk_forward_enabled
        self.walk_forward_train_size = walk_forward_train_size
        self.walk_forward_test_size = walk_forward_test_size
        self.walk_forward_step = walk_forward_step

        # Multiple position settings
        self.allow_multiple_positions = allow_multiple_positions
        self.max_concurrent_trades = max_concurrent_trades
        self.position_size_pct = position_size_pct  # Percentage of available balance per trade

        # Risk Management (Phase 6)
        self.risk_manager = RiskManager(
            initial_balance=initial_balance,
            use_risk_management=use_risk_management,
            risk_per_trade_pct=risk_per_trade_pct,
            max_daily_loss_pct=max_daily_loss_pct,
            max_drawdown_pct=max_drawdown_pct,
            min_risk_reward_ratio=min_risk_reward_ratio,
            position_size_pct=position_size_pct,
        )

        self.balance = self.initial_balance
        self.max_drawdown = 0
        self.max_balance_seen = 0
        self.profit_factor = 0
        self.win_rate = 0
        self.trades: dict[str, Trade] = {}  # All trades (both active and completed)
        self._current_single_trade: Trade | None = None  # Current trade for single position mode
        self.mode = None
        self.telegram_bot = None
        self._trade_counter = 0  # Counter for unique trade IDs

    @property
    def active_trades(self) -> dict[str, Trade]:
        """Get currently active (open) trades"""
        return {trade_id: trade for trade_id, trade in self.trades.items() if not trade.is_closed}

    @property
    def completed_trades(self) -> dict[str, Trade]:
        """Get completed (closed) trades"""
        return {trade_id: trade for trade_id, trade in self.trades.items() if trade.is_closed}

    @abstractmethod
    def check_config(self) -> bool:
        pass

    @abstractmethod
    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """calculates the indicators used in buying and selling

        Args:
            klines (dict[str, Any]): contains the candlesticks information:
            opening price, closing price, high price, low price, opening and
            closing timestamp, volume, etc...

        Returns:
            tuple[Any]: set of indicators
        """
        pass

    @abstractmethod
    def entry_condition(self, df: pd.DataFrame, *, index: int = -1) -> bool:
        """Buy or not depending on the entry condition of the indicators

        Args:
            klines (dict[str, Any]): contains the candlesticks information:
            opening price, closing price, high price, low price, opening and
            closing timestamp, volume, etc...
            index (int, optional): position in the numpy data array. Defaults to -1.

        Returns:
            bool: entry or not to the market
        """
        pass

    @abstractmethod
    def exit_condition(self, df: pd.DataFrame, *, index: int = -1) -> bool:
        """Sell or not depending on the entry condition of the indicators

        Args:
            klines (dict[str, Any]): contains the candlesticks information:
            opening price, closing price, high price, low price, opening and
            closing timestamp, volume, etc...
            index (int, optional): position in the numpy data array. Defaults to -1.

        Returns:
            bool: exit or not from the market
        """
        pass

    def should_enter_new_position(self, df: pd.DataFrame, *, index: int = -1) -> bool:
        """
        Determine if a new position should be entered when multiple positions are allowed.
        By default, uses the original entry_condition logic.
        Override this method for custom multi-position entry logic.

        Args:
            df: DataFrame with indicator data
            index: Current data index

        Returns:
            bool: Whether to enter a new position
        """
        if not self.allow_multiple_positions:
            return not self.position and self.entry_condition(df, index=index)

        # For multiple positions, check if we can add more trades
        if len(self.active_trades) >= self.max_concurrent_trades:
            return False

        return self.entry_condition(df, index=index)

    def should_exit_position(
        self, trade: Trade, df: pd.DataFrame, *, index: int = -1
    ) -> tuple[bool, float | None, str]:
        """
        Determine if a specific position should be exited.
        Uses intra-candle logic to detect if SL/TP was hit within the candle's range,
        for both single- and multiple-position modes. Falls back to the strategy's
        exit_condition (market exit at close price) when no stop_loss/take_profit is
        set on the trade, or neither was hit this candle.

        Args:
            trade: The active trade to evaluate
            df: DataFrame with indicator data
            index: Current data index

        Returns:
            tuple: (should_exit, exit_price, reason)
                - should_exit: Whether to exit this position
                - exit_price: Exact exit price if SL/TP hit, None for market exit
                - reason: Exit reason ("Stop Loss", "Take Profit", "Exit Signal")
        """
        current_candle = df.iloc[index]
        candle_low = current_candle["low"]
        candle_high = current_candle["high"]
        candle_open = current_candle["open"]
        candle_close = current_candle["close"]

        # Check if stop loss is within candle range
        sl_in_range = trade.stop_loss > 0 and candle_low <= trade.stop_loss <= candle_high
        # Check if take profit is within candle range
        tp_in_range = trade.take_profit > 0 and candle_low <= trade.take_profit <= candle_high

        # If both in range, determine which was hit first based on candle direction
        if sl_in_range and tp_in_range:
            return self._determine_intracandle_priority(trade, candle_open, candle_close)

        # Only stop loss in range
        if sl_in_range:
            return True, trade.stop_loss, "Stop Loss"

        # Only take profit in range
        if tp_in_range:
            return True, trade.take_profit, "Take Profit"

        # Use strategy's exit condition (market exit at close price)
        if self.exit_condition(df, index=index):
            return True, None, "Exit Signal"

        return False, None, ""

    def _determine_intracandle_priority(
        self, trade: Trade, candle_open: float, candle_close: float
    ) -> tuple[bool, float, str]:
        """Determine which level (SL or TP) was hit first when both are in candle range

        Args:
            trade: Trade with stop_loss and take_profit set
            candle_open: Candle opening price
            candle_close: Candle closing price

        Returns:
            tuple: (True, exit_price, reason) for the level hit first
        """
        is_bullish = candle_close > candle_open

        if is_bullish:
            # Bullish candle: price went down first (to low), then up (to high)
            # Stop loss (below entry) would be hit before take profit (above entry)
            if trade.stop_loss < candle_open and trade.take_profit > candle_open:
                return True, trade.stop_loss, "Stop Loss"
            # If both on same side, hit the closer one first
            elif abs(candle_open - trade.stop_loss) < abs(candle_open - trade.take_profit):
                return True, trade.stop_loss, "Stop Loss"
            else:
                return True, trade.take_profit, "Take Profit"
        else:
            # Bearish candle: price went up first (to high), then down (to low)
            # Take profit (above entry) would be hit before stop loss (below entry)
            if trade.take_profit > candle_open and trade.stop_loss < candle_open:
                return True, trade.take_profit, "Take Profit"
            # If both on same side, hit the closer one first
            elif abs(candle_open - trade.take_profit) < abs(candle_open - trade.stop_loss):
                return True, trade.take_profit, "Take Profit"
            else:
                return True, trade.stop_loss, "Stop Loss"

    def run(self, mode: str) -> None:
        self.mode = mode
        if not self.check_config():
            msg = "Invalid combination of strategy parameters. Please check your configuration."
            if self.mode != Mode.OPTIMIZATION:
                raise ValueError(msg)
            logger.warning(msg)
            return

        histo_data = {timeframe: get_data(self.symbol, timeframe) for timeframe in self.timeframes}
        data = self.compute_indicators(histo_data)
        if self.mode == Mode.BACKTEST or self.mode == Mode.OPTIMIZATION:
            self.backtest(data)
        elif self.mode == Mode.LIVE:
            self.telegram_bot = TelegramBot(
                bot_token=os.environ.get("TRADE_PRO_TELEGRAM_BOT_TOKEN_ENV"),
                chat_id=os.environ.get("TRADE_PRO_TELEGRAM_CHAT_ID_ENV"),
            )
            self.telegram_bot.send_telegram_message(
                f"[{self.__class__.__name__}] Starting live trade"
            )
            self.live(data, histo_data)

    def live(self, data: pd.DataFrame, histo_data: dict[str, pd.DataFrame]) -> None:
        """Run live trading loop with real-time data"""
        entry_price, entry_time, units = self._init_single_position_vars()
        historical_buffer = histo_data.copy()

        logger.info(f"[{self.__class__.__name__}] Running live trading loop")
        while True:
            historical_buffer = self._fetch_latest_data(historical_buffer)
            data = self.compute_indicators(historical_buffer)
            row = data.iloc[self.start_live_index]

            logger.info(f"[{self.__class__.__name__}] Running entry/exit condition")
            entry_price, entry_time, units = self._process_candle(
                data, row, self.start_live_index, None, entry_price, entry_time, units
            )

            wait_for_next_candle(timeframe=self.timeframes[0])

    def _fetch_latest_data(
        self, historical_buffer: dict[str, pd.DataFrame]
    ) -> dict[str, pd.DataFrame]:
        """Fetch and update latest candle data"""
        logger.info(f"[{self.__class__.__name__}] Fetching new data")
        updated_buffer = {
            timeframe: update_data(
                historical_buffer[timeframe], fetch_candles(self.symbol, timeframe, 50)
            )
            for timeframe in self.timeframes
        }
        logger.info(f"[{self.__class__.__name__}] Computing indicators")
        return updated_buffer

    def backtest(self, data: pd.DataFrame) -> None:
        """run back testing strategy"""
        if self.walk_forward_enabled:
            self._run_walk_forward_backtest(data)
        else:
            self._run_simple_backtest(data)

    def _run_simple_backtest(self, data: pd.DataFrame) -> None:
        """Traditional backtest on entire dataset"""
        entry_price, entry_time, units = self._init_single_position_vars()

        for i in range(self.start_backtest_index, len(data)):
            row = data.iloc[i]
            next_row = data.iloc[i + 1] if i + 1 < len(data) else None
            entry_price, entry_time, units = self._process_candle(
                data, row, i, next_row, entry_price, entry_time, units
            )

        self._finalize_backtest(data)

    def _finalize_backtest(self, data: pd.DataFrame) -> None:
        """Close remaining trades and generate reports"""
        if self.allow_multiple_positions and self.active_trades:
            final_row = data.iloc[-1]
            for trade_id in list(self.active_trades.keys()):
                self._close_active_trade(trade_id, final_row, "End of backtest")

        if len(self.trades) > 0:
            self.resume_backtest(self.trades)
            self.generate_chart(self.symbol, data)

    def _run_walk_forward_backtest(self, data: pd.DataFrame) -> None:
        """Run rolling window validation test"""
        self._print_walk_forward_header()
        window_results = self._execute_walk_forward_windows(data)
        self._print_walk_forward_summary(window_results)

        if len(self.trades) > 0:
            self.resume_backtest(self.trades)
            self.generate_chart(self.symbol, data)

    def _print_walk_forward_header(self) -> None:
        """Print walk-forward test header"""
        logger.info("\n" + "=" * 60)
        logger.info("WALK-FORWARD BACKTEST")
        logger.info("=" * 60)

    def _execute_walk_forward_windows(self, data: pd.DataFrame) -> list[dict]:
        """Execute all walk-forward windows and return results"""
        window_results = []
        current_start = self.start_backtest_index
        window_num = 1

        while current_start + self.walk_forward_train_size + self.walk_forward_test_size <= len(
            data
        ):
            window_result = self._run_single_window(data, current_start, window_num)
            window_results.append(window_result)
            current_start += self.walk_forward_step
            window_num += 1

        return window_results

    def _run_single_window(self, data: pd.DataFrame, current_start: int, window_num: int) -> dict:
        """Run single walk-forward window"""
        train_start, train_end, test_start, test_end = self._calculate_window_indices(
            data, current_start
        )

        self._log_window_info(data, window_num, train_start, train_end, test_start, test_end)
        self._reset_backtest_state()
        self._run_window_backtest(data, test_start, test_end)

        return self._create_window_result(
            data, window_num, train_start, train_end, test_start, test_end
        )

    def _calculate_window_indices(
        self, data: pd.DataFrame, current_start: int
    ) -> tuple[int, int, int, int]:
        """Calculate train and test indices for window"""
        train_start = current_start
        train_end = current_start + self.walk_forward_train_size
        test_start = train_end
        test_end = min(test_start + self.walk_forward_test_size, len(data))
        return train_start, train_end, test_start, test_end

    def _log_window_info(
        self,
        data: pd.DataFrame,
        window_num: int,
        train_start: int,
        train_end: int,
        test_start: int,
        test_end: int,
    ) -> None:
        """Log window date ranges"""
        logger.info(f"\n--- Window {window_num} ---")
        logger.info(
            f"Train: {data.iloc[train_start].name} to {data.iloc[train_end - 1].name} ({train_end - train_start} bars)"
        )
        logger.info(
            f"Test:  {data.iloc[test_start].name} to {data.iloc[test_end - 1].name} ({test_end - test_start} bars)"
        )

    def _run_window_backtest(self, data: pd.DataFrame, test_start: int, test_end: int) -> None:
        """Run backtest for test period of window"""
        entry_price, entry_time, units = self._init_single_position_vars()

        for i in range(test_start, test_end):
            row = data.iloc[i]
            next_row = data.iloc[i + 1] if i + 1 < len(data) else None
            entry_price, entry_time, units = self._process_candle(
                data, row, i, next_row, entry_price, entry_time, units
            )

        self._close_remaining_trades(data, test_end)

    def _close_remaining_trades(self, data: pd.DataFrame, test_end: int) -> None:
        """Close any remaining active trades at end of window"""
        if self.allow_multiple_positions and self.active_trades:
            final_row = data.iloc[test_end - 1]
            for trade_id in list(self.active_trades.keys()):
                self._close_active_trade(trade_id, final_row, "End of window")

    def _create_window_result(
        self,
        data: pd.DataFrame,
        window_num: int,
        train_start: int,
        train_end: int,
        test_start: int,
        test_end: int,
    ) -> dict:
        """Create result dictionary for window"""
        window_trades = len(self.completed_trades)
        window_pnl = sum(t.pnl for t in self.completed_trades.values() if t.pnl is not None)

        logger.info(
            f"Trades: {window_trades} | PnL: ${window_pnl:.2f} | Balance: ${self.balance:.2f}"
        )

        return {
            "window": window_num,
            "train_start": data.iloc[train_start].name,
            "train_end": data.iloc[train_end - 1].name,
            "test_start": data.iloc[test_start].name,
            "test_end": data.iloc[test_end - 1].name,
            "trades": window_trades,
            "pnl": window_pnl,
            "final_balance": self.balance,
        }

    def _print_walk_forward_summary(self, window_results: list[dict]) -> None:
        """Print summary of all walk-forward windows"""
        logger.info("\n" + "=" * 60)
        logger.info("WALK-FORWARD SUMMARY")
        logger.info("=" * 60)

        total_trades = sum(w["trades"] for w in window_results)
        total_pnl = sum(w["pnl"] for w in window_results)
        avg_pnl_per_window = total_pnl / len(window_results) if window_results else 0
        profitable_windows = sum(1 for w in window_results if w["pnl"] > 0)

        logger.info(f"Total Windows: {len(window_results)}")
        logger.info(
            f"Profitable Windows: {profitable_windows}/{len(window_results)} ({profitable_windows / len(window_results) * 100:.1f}%)"
        )
        logger.info(f"Total Trades: {total_trades}")
        logger.info(f"Total PnL: ${total_pnl:.2f}")
        logger.info(f"Avg PnL per Window: ${avg_pnl_per_window:.2f}")
        logger.info(f"Final Balance: ${self.balance:.2f}")

    def _reset_backtest_state(self) -> None:
        """Reset state between walk-forward windows"""
        self.balance = self.initial_balance
        self.position = False
        self.trades = {}
        self._current_single_trade = None
        self._trade_counter = 0
        self.max_drawdown = 0
        self.max_balance_seen = 0
        # Reset risk management state
        self.risk_manager.reset(self.initial_balance)

    def _init_single_position_vars(self) -> tuple[float, pd.Timestamp, float]:
        """Initialize single position mode variables"""
        return 0, pd.NaT, 0

    def _generate_trade_id(self, entry_time: pd.Timestamp, trade_type: str = "single") -> str:
        """Generate unique trade ID"""
        self._trade_counter += 1
        return f"{trade_type}_{self.symbol}_{entry_time}_{self._trade_counter}"

    def _process_candle(
        self,
        data: pd.DataFrame,
        row: pd.Series,
        index: int,
        next_row: pd.Series | None,
        entry_price: float,
        entry_time: pd.Timestamp,
        units: float,
    ) -> tuple[float, pd.Timestamp, float]:
        """Process single candle for entry/exit logic"""
        if self._check_circuit_breakers(row.name):
            return self._process_circuit_breaker_exits(
                data, row, index, next_row, entry_price, entry_time, units
            )

        if self.allow_multiple_positions:
            self._handle_multiple_positions(data, row, index, next_row)
            return entry_price, entry_time, units

        # Single position mode
        if self.entry_condition(data, index=index):
            return self.execute_entry(row, next_row)
        elif self._current_single_trade:
            # Check SL/TP and exit conditions for active trade
            should_exit, exit_price, reason = self.should_exit_position(
                self._current_single_trade, data, index=index
            )
            if should_exit:
                self.execute_exit(row, entry_price, entry_time, units, next_row, exit_price, reason)
        elif self.exit_condition(data, index=index):
            self.execute_exit(row, entry_price, entry_time, units, next_row)

        return entry_price, entry_time, units

    def _process_circuit_breaker_exits(
        self,
        data: pd.DataFrame,
        row: pd.Series,
        index: int,
        next_row: pd.Series | None,
        entry_price: float,
        entry_time: pd.Timestamp,
        units: float,
    ) -> tuple[float, pd.Timestamp, float]:
        """Process exits only when circuit breaker is active (no new entries allowed)"""
        if self.allow_multiple_positions:
            trades_to_close = []
            for trade_id, trade in self.active_trades.items():
                should_exit, exit_price, reason = self.should_exit_position(
                    trade, data, index=index
                )
                if should_exit:
                    trades_to_close.append((trade_id, exit_price, f"Circuit breaker - {reason}"))

            for trade_id, exit_price, reason in trades_to_close:
                self._close_active_trade(trade_id, row, reason, next_row, exit_price)
        elif self._current_single_trade:
            # Check SL/TP for single position mode
            should_exit, exit_price, reason = self.should_exit_position(
                self._current_single_trade, data, index=index
            )
            if should_exit:
                self.execute_exit(
                    row,
                    entry_price,
                    entry_time,
                    units,
                    next_row,
                    exit_price,
                    f"Circuit breaker - {reason}",
                )

        return entry_price, entry_time, units

    def execute_entry(
        self,
        row: pd.Series,
        next_row: pd.Series | None = None,
        stop_loss: float = 0,
    ) -> tuple[float, pd.Timestamp, float]:
        """Execute trade entry for single position mode"""
        if self.allow_multiple_positions:
            trade = self._execute_multiple_entry(row, next_row, stop_loss)
            return trade.entry_price, trade.entry_time, trade.units

        execution_price = self._get_execution_price(row, next_row)
        entry_price = self._calculate_entry_price(execution_price)
        position_size, units = self._calculate_position_size_and_units(
            entry_price, stop_loss, self.balance
        )
        if units <= 0:
            logger.warning(
                f"[{self.__class__.__name__}] Skipping entry at {row.name} — insufficient "
                f"balance (${self.balance:.2f}) to open a position"
            )
            return self._init_single_position_vars()

        entry_time = row.name

        self._create_and_store_trade(entry_time, entry_price, units, position_size)
        self.position = True
        self._log_entry(entry_time, entry_price)

        return entry_price, entry_time, units

    def _calculate_position_size_and_units(
        self, entry_price: float, stop_loss: float, available_capital: float
    ) -> tuple[float, float]:
        """Calculate position size and units based on risk management settings

        Always routed through the risk manager, which itself falls back to
        ``available_capital * position_size_pct`` when risk-based sizing isn't
        applicable (risk management disabled, or no stop_loss to size against) —
        this guarantees position_size_pct is honored in every case, not only when
        risk management is on.

        Returns:
            tuple: (position_size, units)
        """
        if available_capital <= 0:
            return 0.0, 0.0

        position_size = self.risk_manager.calculate_position_size(
            entry_price, stop_loss, available_capital
        )
        units = position_size / entry_price

        return position_size, units

    def _get_execution_price(self, row: pd.Series, next_row: pd.Series | None) -> float:
        """Get realistic execution price based on settings"""
        if self.use_next_candle_open and next_row is not None:
            return next_row["open"]
        return row["close"]

    def _calculate_entry_price(self, execution_price: float) -> float:
        """Apply slippage and commission to execution price"""
        return execution_price * (1 + self.slippage + self.commission)

    def _calculate_exit_price(self, execution_price: float) -> float:
        """Apply slippage and commission to exit price"""
        return execution_price * (1 - self.slippage - self.commission)

    def _create_and_store_trade(
        self, entry_time: pd.Timestamp, entry_price: float, units: float, position_size: float
    ) -> None:
        """Create trade object and store in trades dict"""
        trade_id = self._generate_trade_id(entry_time, "single")
        self._current_single_trade = Trade(
            id=trade_id,
            entry_time=entry_time,
            entry_price=entry_price,
            units=units,
            position_size=position_size,
        )
        self.trades[trade_id] = self._current_single_trade

    def _log_entry(self, entry_time: pd.Timestamp, entry_price: float) -> None:
        """Log entry message to console and telegram"""
        msg = (
            f"📈 [ENTRY] [{self.__class__.__name__}] {self.symbol} {entry_time} @ {entry_price:.2f}"
        )
        self._log_message(msg)

    def execute_exit(
        self,
        row: pd.Series,
        entry_price: float,
        entry_time: pd.Timestamp,
        units: float,
        next_row: pd.Series | None = None,
        exit_price: float | None = None,
        reason: str = "Exit condition met",
    ) -> None:
        """Execute trade exit for single position mode

        Args:
            row: Current candle data
            entry_price: Entry price of the trade
            entry_time: Entry time of the trade
            units: Number of units in the trade
            next_row: Next candle data (for look-ahead bias fix)
            exit_price: Exact exit price if SL/TP hit, None for market exit
            reason: Exit reason
        """
        if self.allow_multiple_positions:
            logger.warning(
                "execute_exit called in multiple position mode - use _close_active_trade instead"
            )
            return

        trade = self._get_or_create_trade(entry_price, entry_time, units)
        closed_trade = self._close_trade_and_record(trade, row, reason, next_row, exit_price)

        self._current_single_trade = None
        self.position = False
        self._log_exit(closed_trade)

    def _get_or_create_trade(
        self, entry_price: float, entry_time: pd.Timestamp, units: float
    ) -> Trade:
        """Get existing trade or create from parameters for backward compatibility"""
        if hasattr(self, "_current_single_trade") and self._current_single_trade:
            return self._current_single_trade

        position_size = units * entry_price
        trade_id = self._generate_trade_id(entry_time, "single")
        trade = Trade(
            id=trade_id,
            entry_time=entry_time,
            entry_price=entry_price,
            units=units,
            position_size=position_size,
        )
        self.trades[trade_id] = trade
        return trade

    def _log_exit(self, closed_trade: Trade) -> None:
        """Log exit message to console and telegram"""
        msg = (
            f"📉 [LONG EXIT] [{self.__class__.__name__}] {self.symbol} Time: {closed_trade.exit_time} Price: ${closed_trade.exit_price:.2f}."
            f"PnL: ${closed_trade.pnl:.2f} | Return: {(closed_trade.return_pct * 100):.2f}%"
        )
        if self.mode == Mode.BACKTEST:
            logger.info(msg)
        if self.mode == Mode.LIVE:
            logger.info(msg)
            if hasattr(self, "telegram_bot") and self.telegram_bot:
                self.telegram_bot.send_telegram_message(msg)

    def resume_backtest(self, trades: dict[str, Trade]):
        # Calculate performance metrics
        metrics = self._calculate_performance_metrics()

        # Log results
        if self.mode == Mode.BACKTEST:
            self._log_backtest_results(metrics)

    def _calculate_performance_metrics(self) -> dict:
        """Calculate all performance metrics from completed trades"""
        completed_trades = self.completed_trades
        trade_list = list(completed_trades.values())
        returns = [trade.return_pct for trade in trade_list if trade.return_pct is not None]
        wins = [trade for trade in trade_list if trade.is_profitable]
        losses = [trade for trade in trade_list if not trade.is_profitable]

        total_wins = sum(trade.pnl for trade in wins if trade.pnl is not None)
        total_losses = abs(sum(trade.pnl for trade in losses if trade.pnl is not None))

        value_weighted_win_rate = (
            total_wins / (total_wins + total_losses) if (total_wins + total_losses) > 0 else 0
        )
        self.win_rate = len(wins) / len(trade_list) if trade_list else 0
        self.profit_factor = total_wins / total_losses if total_losses != 0 else float("inf")

        # Calculate drawdown metrics
        self._calculate_drawdown_metrics(trade_list)

        total_pnl = sum(trade.pnl for trade in trade_list if trade.pnl is not None)

        sharpe_like = float("nan")
        if len(returns) > 0:
            sharpe_like = np.mean(returns) / (np.std(returns) + 1e-9)  # avoid div by zero

        return {
            "trade_list": trade_list,
            "wins": wins,
            "losses": losses,
            "value_weighted_win_rate": value_weighted_win_rate,
            "total_pnl": total_pnl,
            "sharpe_like": sharpe_like,
        }

    def _calculate_drawdown_metrics(self, trade_list: list[Trade]) -> None:
        """Calculate max drawdown and max balance from trade history"""
        pnl_values = [trade.pnl for trade in trade_list if trade.pnl is not None]
        if pnl_values:
            pnl_series = pd.Series(pnl_values)
            cumulative_pnl = pnl_series.cumsum()
            self.max_drawdown = (cumulative_pnl.cummax() - cumulative_pnl).max()

            cumulative_balance = self.initial_balance + cumulative_pnl
            self.max_balance_seen = cumulative_balance.max()
        else:
            self.max_drawdown = 0
            self.max_balance_seen = self.initial_balance

    def _log_backtest_results(self, metrics: dict) -> None:
        """Log backtest results including trade summary and statistics"""
        self._log_trade_summary(metrics["trade_list"])
        self._log_performance_stats(metrics)
        self._log_risk_management_stats()

    def _log_trade_summary(self, trade_list: list[Trade]) -> None:
        """Log individual trade details"""
        logger.info("\nTrade Summary:")
        for i, trade in enumerate(trade_list):
            logger.info(
                f"Trade {i + 1}: {trade.entry_time} -> {trade.exit_time} | "
                f"Entry: ${trade.entry_price:.2f} | Exit: ${trade.exit_price:.2f} | "
                f"PnL: ${trade.pnl:.2f} | Return: {(trade.return_pct * 100):.2f}%"
            )

    def _log_performance_stats(self, metrics: dict) -> None:
        """Log overall performance statistics"""
        trade_list = metrics["trade_list"]
        wins = metrics["wins"]
        losses = metrics["losses"]
        value_weighted_win_rate = metrics["value_weighted_win_rate"]
        total_pnl = metrics["total_pnl"]
        sharpe_like = metrics["sharpe_like"]

        logger.info("\nStats:")
        logger.info(f"Total Trades: {len(trade_list)}")
        logger.info(f"Win Trades: {len(wins)}")
        logger.info(f"Lose Trades: {len(losses)}")
        logger.info(f"Max win: ${max([trade.pnl for trade in wins], default=0):.2f}")
        logger.info(f"Max lose: ${min([trade.pnl for trade in losses], default=0):.2f}")
        logger.info(f"Win Rate (Count-Based): {(self.win_rate * 100):.2f}%")
        logger.info(f"Win Rate (PnL-Weighted): {(value_weighted_win_rate * 100):.2f}%")
        logger.info(f"Profit Factor: {self.profit_factor:.2f}")
        logger.info(f"Sharpe-like Ratio (return_pct/std): {sharpe_like:.2f}")
        logger.info(f"Max Drawdown: ${self.max_drawdown:.2f}")
        logger.info(f"Max Balance Seen: ${self.max_balance_seen:.2f}")
        logger.info(f"Total PnL: ${total_pnl:.2f}")
        logger.info(f"Final Balance: ${(self.balance):.2f}")

    def _log_risk_management_stats(self) -> None:
        """Log risk management metrics if enabled"""
        if self.risk_manager.use_risk_management:
            risk_metrics = self.get_risk_metrics()
            logger.info(f"Risk per Trade: {risk_metrics['risk_per_trade'] * 100:.2f}%")
            logger.info(f"Min Risk/Reward Ratio: {risk_metrics['min_risk_reward']:.2f}")
            logger.info(f"Max Daily Loss Limit: {risk_metrics['daily_loss_limit'] * 100:.2f}%")
            logger.info(f"Max Drawdown Limit: {risk_metrics['drawdown_limit'] * 100:.2f}%")
            logger.info(
                f"Circuit Breaker Triggered: {'Yes' if risk_metrics['circuit_breaker_active'] else 'No'}"
            )

    def generate_chart(
        self,
        symbol: str,
        df: pd.DataFrame,
    ):
        if self.mode == Mode.BACKTEST:
            # Pass completed trades to chart functions
            completed_trades = self.completed_trades
            plot_price_chart(symbol, self.__class__.__name__, df, completed_trades)
            plot_equity_curve(symbol, self.__class__.__name__, completed_trades)

    def _handle_multiple_positions(
        self, data: pd.DataFrame, row: pd.Series, index: int, next_row: pd.Series | None = None
    ) -> None:
        """Handle multiple position logic for both backtesting and live trading"""
        # Check for new entries
        if self.should_enter_new_position(data, index=index):
            stop_loss = self._calculate_multi_entry_stop_loss(row, next_row)
            self._execute_multiple_entry(row, next_row, stop_loss)

        # Check exits for all active trades
        trades_to_close = []
        for trade_id, trade in self.active_trades.items():
            should_exit, exit_price, reason = self.should_exit_position(trade, data, index=index)
            if should_exit:
                trades_to_close.append((trade_id, exit_price, reason))

        # Close trades that meet exit conditions
        for trade_id, exit_price, reason in trades_to_close:
            self._close_active_trade(trade_id, row, reason, next_row, exit_price)

    def _calculate_multi_entry_stop_loss(
        self, row: pd.Series, next_row: pd.Series | None = None
    ) -> float:
        """
        Compute the stop-loss price to size a new multi-position entry against,
        *before* the position is sized. Defaults to 0 (no risk-based sizing).

        Override this in a strategy that wants per-trade ATR/other stops to
        actually drive position sizing in multi-position mode — setting
        trade.stop_loss only *after* the trade is created is too late, since
        sizing has already happened by then.
        """
        return 0

    def _execute_multiple_entry(
        self, row: pd.Series, next_row: pd.Series | None = None, stop_loss: float = 0
    ) -> Trade:
        """Execute entry for multiple position mode"""
        execution_price = self._get_execution_price(row, next_row)
        entry_price = self._calculate_entry_price(execution_price)

        available_balance = self._get_available_balance()
        position_value, units = self._calculate_position_size_and_units(
            entry_price, stop_loss, available_balance
        )

        trade_id = self._generate_trade_id(row.name, "multi")
        trade = Trade(
            id=trade_id,
            entry_time=row.name,
            entry_price=entry_price,
            units=units,
            position_size=position_value,
            stop_loss=stop_loss,
        )

        if units <= 0:
            logger.warning(
                f"[{self.__class__.__name__}] Skipping multi-entry at {row.name} — "
                f"insufficient available balance (${available_balance:.2f})"
            )
            return trade

        self.trades[trade_id] = trade
        self.position = True

        self._log_multi_entry(trade, position_value)
        return trade

    def _log_multi_entry(self, trade: Trade, position_value: float) -> None:
        """Log multiple position entry message"""
        msg = (
            f"📈 [MULTI-ENTRY] [{self.__class__.__name__}] {self.symbol} {trade.entry_time} @ {trade.entry_price:.2f} "
            f"| Position: {position_value:.2f} | Units: {trade.units:.6f} | Active trades: {len(self.active_trades)}"
        )
        self._log_message(msg)

    def _close_trade_and_record(
        self,
        trade: Trade,
        row: pd.Series,
        reason: str = "",
        next_row: pd.Series | None = None,
        forced_exit_price: float | None = None,
    ) -> Trade:
        """Close trade and update balance

        Args:
            trade: Trade to close
            row: Current candle data
            reason: Reason for exit
            next_row: Next candle data (for look-ahead bias fix)
            forced_exit_price: Exact exit price for SL/TP (no slippage, only commission)
        """
        exit_time = row.name

        if forced_exit_price is not None:
            # SL/TP execution: limit order at exact price (only commission, no slippage)
            exit_price = forced_exit_price * (1 - self.commission)
        else:
            # Market exit: use close/open price with slippage and commission
            execution_price = self._get_execution_price(row, next_row)
            exit_price = self._calculate_exit_price(execution_price)

        trade.close_trade(exit_time, exit_price, self.balance, reason)
        self.balance += trade.pnl

        return trade

    def _close_active_trade(
        self,
        trade_id: str,
        row: pd.Series,
        reason: str = "",
        next_row: pd.Series | None = None,
        exit_price: float | None = None,
    ) -> None:
        """Close an active trade in multiple position mode

        Args:
            trade_id: ID of trade to close
            row: Current candle data
            reason: Reason for exit
            next_row: Next candle data (for look-ahead bias fix)
            exit_price: Exact exit price if SL/TP hit, None for market exit
        """
        if trade_id not in self.trades or self.trades[trade_id].is_closed:
            return

        trade = self.trades[trade_id]
        closed_trade = self._close_trade_and_record(trade, row, reason, next_row, exit_price)
        self.position = len(self.active_trades) > 0

        self._log_multi_exit(closed_trade, reason)

    def _log_multi_exit(self, closed_trade: Trade, reason: str) -> None:
        """Log multiple position exit message"""
        msg = (
            f"📉 [MULTI-EXIT] [{self.__class__.__name__}] {self.symbol} {closed_trade.exit_time} @ {closed_trade.exit_price:.2f} "
            f"| PnL: ${closed_trade.pnl:.2f} | Return: {(closed_trade.return_pct * 100):.2f}% | Reason: {reason} "
            f"| Active trades: {len(self.active_trades)}"
        )
        self._log_message(msg)

    def _log_message(self, msg: str) -> None:
        """Centralized logging for backtest and live modes"""
        if self.mode == Mode.BACKTEST:
            logger.info(msg)
        elif self.mode == Mode.LIVE:
            logger.info(msg)
            self.telegram_bot.send_telegram_message(msg)

    def _get_available_balance(self) -> float:
        """Calculate available balance for new positions"""
        if not self.allow_multiple_positions:
            return self.balance

        # Total value locked in active trades
        locked_value = sum(trade.position_size for trade in self.active_trades.values())

        # Available balance is current balance minus what's locked
        # Note: Current balance already includes unrealized PnL from price movements
        return max(0, self.balance - locked_value)

    def _check_circuit_breakers(self, current_time: pd.Timestamp) -> bool:
        """Check if circuit breakers have been triggered"""
        return self.risk_manager.check_circuit_breakers(
            current_time, self.balance, self.mode, self.telegram_bot
        )

    def _calculate_risk_based_position_size(
        self, entry_price: float, stop_loss_price: float, available_capital: float
    ) -> float:
        """Calculate position size based on risk per trade (Phase 6)"""
        return self.risk_manager.calculate_position_size(
            entry_price, stop_loss_price, available_capital
        )

    def _validate_trade_risk_reward(
        self, entry_price: float, stop_loss: float, take_profit: float
    ) -> bool:
        """Validate trade meets minimum risk/reward ratio (Phase 6)"""
        return self.risk_manager.validate_risk_reward(entry_price, stop_loss, take_profit)

    def get_risk_metrics(self) -> dict:
        """Get current risk management metrics (Phase 6)"""
        return self.risk_manager.get_metrics(self.balance)

    def get_active_trades_summary(self) -> dict:
        """Get summary of active trades for monitoring"""
        if not self.active_trades:
            return {"count": 0, "total_position_value": 0, "trades": []}

        total_value = sum(trade.position_size for trade in self.active_trades.values())
        trades_info = [
            {
                "id": trade.id,
                "entry_time": trade.entry_time,
                "entry_price": trade.entry_price,
                "position_size": trade.position_size,
                "units": trade.units,
            }
            for trade in self.active_trades.values()
        ]

        return {
            "count": len(self.active_trades),
            "total_position_value": total_value,
            "available_balance": self._get_available_balance(),
            "trades": trades_info,
        }
