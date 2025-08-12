import logging
from abc import abstractmethod
from enum import StrEnum
from typing import Any

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
    ):
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.position = position
        self.timeframes = timeframes
        self.commission = commission
        self.slippage = slippage
        self.start_backtest_index = start_backtest_index
        self.start_live_index = start_live_index

        self.balance = self.initial_balance
        self.max_drawdown = 0
        self.max_balance_seen = 0
        self.profit_factor = 0
        self.win_rate = 0
        self.trades: list[dict[str, int | float]] = []
        self.mode = None
        self.telegram_bot = None

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
            if self.entry_condition(data, index=self.start_live_index):
                entry_price, entry_time, units = self.execute_entry(row)
            elif self.exit_condition(data, index=self.start_live_index):
                self.execute_exit(row, entry_price, entry_time, units)
            wait_for_next_candle(timeframe=self.timeframes[0])

    def backtest(self, data: pd.DataFrame) -> None:
        """run back testing strategy"""
        entry_price = 0
        entry_time = pd.NaT
        units = 0
        for i in range(self.start_backtest_index, len(data)):
            row = data.iloc[i]
            if self.entry_condition(data, index=i):
                entry_price, entry_time, units = self.execute_entry(row)
            elif self.exit_condition(data, index=i):
                self.execute_exit(row, entry_price, entry_time, units)

        if len(self.trades) > 0:
            self.resume_backtest(self.trades)
            self.generate_chart(self.symbol, data, self.trades)

    def execute_entry(
        self,
        row: pd.Series,
    ) -> tuple[float, pd.Timestamp, float]:
        entry_price = row["close"] * (1 + self.slippage + self.commission)
        units = self.balance / entry_price
        self.position = True
        entry_time = row.name
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
        exit_price = row["close"] * (1 - self.slippage - self.commission)
        pnl = (exit_price - entry_price) * units
        exit_time = row.name
        return_pct = pnl / (units * entry_price)
        self.trades.append(
            {
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "return_pct": return_pct,
                "old_balance": self.balance,
                "new_balance": self.balance + pnl,
            }
        )
        self.balance += pnl
        self.position = False
        msg = (
            f"📉 [LONG EXIT] [{self.__class__.__name__}] {self.symbol} Time: {exit_time} Price: ${exit_price:.2f}."
            f"PnL: ${pnl:.2f} | Return: {(return_pct * 100):.2f}%"
        )
        if self.mode == Mode.BACKTEST:
            logger.info(msg)
        if self.mode == Mode.LIVE:
            logger.info(msg)
            self.telegram_bot.send_telegram_message(msg)

    def resume_backtest(self, trades: list[dict[str, Any]]):
        trade_df = pd.DataFrame(trades)

        # Performance Metrics
        returns = [t["return_pct"] for t in trades]
        wins = trade_df[trade_df["pnl"] > 0]
        losses = trade_df[trade_df["pnl"] <= 0]
        total_wins = wins["pnl"].sum()
        total_losses = abs(losses["pnl"].sum())
        value_weighted_win_rate = (
            total_wins / (total_wins + total_losses) if (total_wins + total_losses) > 0 else 0
        )
        self.win_rate = len(wins) / len(trade_df)
        self.profit_factor = total_wins / total_losses if total_losses != 0 else float("inf")
        self.max_drawdown = (trade_df["pnl"].cumsum().cummax() - trade_df["pnl"].cumsum()).max()
        total_pnl = trade_df["pnl"].sum()
        cumulative_balance = self.initial_balance + trade_df["pnl"].cumsum()
        self.max_balance_seen = cumulative_balance.max()
        sharpe_like = float("nan")
        if len(returns) > 0:
            sharpe_like = np.mean(returns) / (np.std(returns) + 1e-9)  # avoid div by zero

        if self.mode == Mode.BACKTEST:
            logger.info("\nTrade Summary:")
            logger.info(trade_df)

            logger.info("\nStats:")
            logger.info(f"Total Trades: {len(trade_df)}")
            logger.info(f"Win Trades: {len(wins)}")
            logger.info(f"Lose Trades: {len(losses)}")
            logger.info(f"Max win: ${wins['pnl'].max():.2f}")
            logger.info(f"Max lose: ${losses['pnl'].min():.2f}")
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
        trades: list[dict[str, Any]],
    ):
        if self.mode == Mode.BACKTEST:
            plot_price_chart(symbol, self.__class__.__name__, df, trades)
            plot_equity_curve(symbol, self.__class__.__name__, trades)
