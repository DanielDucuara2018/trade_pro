import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np
import pandas as pd

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
    ):
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.position = position  # Keep for backward compatibility
        self.timeframes = timeframes
        self.commission = commission
        self.slippage = slippage
        self.start_backtest_index = start_backtest_index
        self.start_live_index = start_live_index

        # Multiple position settings
        self.allow_multiple_positions = allow_multiple_positions
        self.max_concurrent_trades = max_concurrent_trades
        self.position_size_pct = position_size_pct  # Percentage of available balance per trade

        self.balance = self.initial_balance
        self.max_drawdown = 0
        self.max_balance_seen = 0
        self.profit_factor = 0
        self.win_rate = 0
        self.trades: dict[str, Trade] = {}  # All trades (both active and completed)
        self._current_single_trade: Trade | None = None  # Current trade for single position mode
        self.mode = None
        self.telegram_bot = None

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

    def should_exit_position(self, trade: Trade, df: pd.DataFrame, *, index: int = -1) -> bool:
        """
        Determine if a specific position should be exited when multiple positions are allowed.
        By default, uses the original exit_condition logic.
        Override this method for custom per-trade exit logic.

        Args:
            trade: The active trade to evaluate
            df: DataFrame with indicator data
            index: Current data index

        Returns:
            bool: Whether to exit this specific position
        """
        if not self.allow_multiple_positions:
            return self.position and self.exit_condition(df, index=index)

        # Check stop loss and take profit first
        current_price = df.iloc[index]["close"]
        if trade.stop_loss > 0 and current_price <= trade.stop_loss:
            return True
        if trade.take_profit > 0 and current_price >= trade.take_profit:
            return True

        # Use strategy's exit condition
        return self.exit_condition(df, index=index)

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
            self.telegram_bot = TelegramBot(bot_token="your_token", chat_id="your_chat_id")
            self.telegram_bot.send_telegram_message(
                f"[{self.__class__.__name__}] Starting live trade"
            )
            self.live(data, histo_data)

    def live(self, data: pd.DataFrame, histo_data: dict[str, pd.DataFrame]) -> None:
        """run trading strategy"""
        # Legacy single position variables
        entry_price = 0
        entry_time = pd.NaT
        units = 0

        historical_buffer = histo_data.copy()
        logger.info(f"[{self.__class__.__name__}] Running live trading loop")
        while True:
            logger.info(f"[{self.__class__.__name__}] Fetching new data")
            historical_buffer = {
                timeframe: update_data(
                    historical_buffer[timeframe], fetch_candles(self.symbol, timeframe, 50)
                )
                for timeframe in self.timeframes
            }
            logger.info(f"[{self.__class__.__name__}] Computing indicators")
            data = self.compute_indicators(historical_buffer)

            row = data.iloc[self.start_live_index]
            logger.info(f"[{self.__class__.__name__}] Running entry/exit condition")

            if self.allow_multiple_positions:
                # Handle multiple positions
                self._handle_multiple_positions(data, row, self.start_live_index)
            else:
                # Legacy single position logic
                if self.entry_condition(data, index=self.start_live_index):
                    entry_price, entry_time, units = self.execute_entry(row)
                elif self.exit_condition(data, index=self.start_live_index):
                    self.execute_exit(row, entry_price, entry_time, units)

            wait_for_next_candle(timeframe=self.timeframes[0])

    def backtest(self, data: pd.DataFrame) -> None:
        """run back testing strategy"""
        # Legacy single position variables
        entry_price = 0
        entry_time = pd.NaT
        units = 0

        for i in range(self.start_backtest_index, len(data)):
            row = data.iloc[i]

            if self.allow_multiple_positions:
                # Handle multiple positions
                self._handle_multiple_positions(data, row, i)
            else:
                # Legacy single position logic
                if self.entry_condition(data, index=i):
                    entry_price, entry_time, units = self.execute_entry(row)
                elif self.exit_condition(data, index=i):
                    self.execute_exit(row, entry_price, entry_time, units)

        # Close any remaining active trades at the end of backtest
        if self.allow_multiple_positions and self.active_trades:
            final_row = data.iloc[-1]
            for trade_id in list(self.active_trades.keys()):
                self._close_active_trade(trade_id, final_row, "End of backtest")

        if len(self.trades) > 0:
            self.resume_backtest(self.trades)
            self.generate_chart(self.symbol, data, self.trades)

    def execute_entry(
        self,
        row: pd.Series,
    ) -> tuple[float, pd.Timestamp, float]:
        """Legacy single position entry - maintained for backward compatibility"""
        if self.allow_multiple_positions:
            # If using multiple positions, delegate to new system
            trade = self._execute_multiple_entry(row)
            return trade.entry_price, trade.entry_time, trade.units

        # Original single position logic using Trade dataclass for consistency
        entry_price = row["close"] * (1 + self.slippage + self.commission)
        units = self.balance / entry_price
        position_size = units * entry_price
        entry_time = row.name

        # Create and store trade in unified trades dict
        trade_id = f"single_{self.symbol}_{entry_time}"
        self._current_single_trade = Trade(
            id=trade_id,
            entry_time=entry_time,
            entry_price=entry_price,
            units=units,
            position_size=position_size,
        )
        self.trades[trade_id] = self._current_single_trade

        self.position = True

        msg = (
            f"📈 [ENTRY] [{self.__class__.__name__}] {self.symbol} {entry_time} @ {entry_price:.2f}"
        )
        if self.mode == Mode.BACKTEST:
            logger.info(msg)
        if self.mode == Mode.LIVE:
            logger.info(msg)
            self.telegram_bot.send_telegram_message(msg)
        return entry_price, entry_time, units

    def execute_exit(
        self,
        row: pd.Series,
        entry_price: float,
        entry_time: pd.Timestamp,
        units: float,
    ) -> None:
        """Legacy single position exit - maintained for backward compatibility"""
        if self.allow_multiple_positions:
            # For multiple positions, this method is not used directly
            # Exit logic is handled by should_exit_position and _close_active_trade
            logger.warning(
                "execute_exit called in multiple position mode - use _close_active_trade instead"
            )
            return

        # Use stored trade if available, otherwise create new Trade object
        if hasattr(self, "_current_single_trade") and self._current_single_trade:
            trade = self._current_single_trade
        else:
            # Fallback: create Trade object from parameters (for backward compatibility)
            position_size = units * entry_price
            trade_id = f"single_{self.symbol}_{entry_time}"
            trade = Trade(
                id=trade_id,
                entry_time=entry_time,
                entry_price=entry_price,
                units=units,
                position_size=position_size,
            )
            self.trades[trade_id] = trade

        # Close the trade using unified method
        closed_trade = self._close_trade_and_record(trade, row, "Exit condition met")

        # Clear stored trade and update legacy position flag
        self._current_single_trade = None
        self.position = False

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
        # Performance Metrics using only completed trades
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

        # Calculate drawdown using PnL values directly
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

        total_pnl = sum(trade.pnl for trade in trade_list if trade.pnl is not None)

        sharpe_like = float("nan")
        if len(returns) > 0:
            sharpe_like = np.mean(returns) / (np.std(returns) + 1e-9)  # avoid div by zero

        if self.mode == Mode.BACKTEST:
            logger.info("\nTrade Summary:")
            # Create a simple summary table using Trade attributes
            for i, trade in enumerate(trade_list):
                logger.info(
                    f"Trade {i + 1}: {trade.entry_time} -> {trade.exit_time} | "
                    f"Entry: ${trade.entry_price:.2f} | Exit: ${trade.exit_price:.2f} | "
                    f"PnL: ${trade.pnl:.2f} | Return: {(trade.return_pct * 100):.2f}%"
                )

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

    def generate_chart(
        self,
        symbol: str,
        df: pd.DataFrame,
        trades: dict[str, Trade],
    ):
        if self.mode == Mode.BACKTEST:
            # Pass completed trades to chart functions
            completed_trades = self.completed_trades
            plot_price_chart(symbol, self.__class__.__name__, df, completed_trades)
            plot_equity_curve(symbol, self.__class__.__name__, completed_trades)

    def _handle_multiple_positions(self, data: pd.DataFrame, row: pd.Series, index: int) -> None:
        """Handle multiple position logic for both backtesting and live trading"""
        # Check for new entries
        if self.should_enter_new_position(data, index=index):
            self._execute_multiple_entry(row)

        # Check exits for all active trades
        trades_to_close = []
        for trade_id, trade in self.active_trades.items():
            if self.should_exit_position(trade, data, index=index):
                trades_to_close.append(trade_id)

        # Close trades that meet exit conditions
        for trade_id in trades_to_close:
            self._close_active_trade(trade_id, row, "Exit condition met")

    def _execute_multiple_entry(self, row: pd.Series) -> Trade:
        """Execute entry for multiple position strategy"""
        entry_price = row["close"] * (1 + self.slippage + self.commission)

        # Calculate position size based on available balance and percentage allocation
        available_balance = self._get_available_balance()
        position_value = available_balance * self.position_size_pct
        units = position_value / entry_price

        # Generate unique trade ID
        trade_id = f"{self.symbol}_{row.name}_{len(self.active_trades)}"

        # Create trade object
        trade = Trade(
            id=trade_id,
            entry_time=row.name,
            entry_price=entry_price,
            units=units,
            position_size=position_value,
        )

        # Add to trades (will be active since not closed)
        self.trades[trade_id] = trade

        # Update legacy position flag for backward compatibility
        self.position = True

        msg = (
            f"📈 [MULTI-ENTRY] [{self.__class__.__name__}] {self.symbol} {trade.entry_time} @ {entry_price:.2f} "
            f"| Position: {position_value:.2f} | Units: {units:.6f} | Active trades: {len(self.active_trades)}"
        )

        if self.mode == Mode.BACKTEST:
            logger.info(msg)
        if self.mode == Mode.LIVE:
            logger.info(msg)
            self.telegram_bot.send_telegram_message(msg)

        return trade

    def _close_trade_and_record(self, trade: Trade, row: pd.Series, reason: str = "") -> Trade:
        """
        Unified method to close a trade and record it in trade history.
        Works for both single and multiple position modes.
        Returns the closed Trade object.
        """
        exit_price = row["close"] * (1 - self.slippage - self.commission)
        exit_time = row.name

        # Close the trade (this calculates PnL and other metrics)
        trade.close_trade(exit_time, exit_price, self.balance, reason)

        # Trade is already in self.trades, just update balance
        self.balance += trade.pnl

        return trade

    def _close_active_trade(self, trade_id: str, row: pd.Series, reason: str = "") -> None:
        """Close an active trade and record it in trade history"""
        if trade_id not in self.trades or self.trades[trade_id].is_closed:
            return

        trade = self.trades[trade_id]

        # Use unified close method
        closed_trade = self._close_trade_and_record(trade, row, reason)

        # Update legacy position flag
        self.position = len(self.active_trades) > 0

        msg = (
            f"📉 [MULTI-EXIT] [{self.__class__.__name__}] {self.symbol} {closed_trade.exit_time} @ {closed_trade.exit_price:.2f} "
            f"| PnL: ${closed_trade.pnl:.2f} | Return: {(closed_trade.return_pct * 100):.2f}% | Reason: {reason} "
            f"| Active trades: {len(self.active_trades)}"
        )

        if self.mode == Mode.BACKTEST:
            logger.info(msg)
        if self.mode == Mode.LIVE:
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
