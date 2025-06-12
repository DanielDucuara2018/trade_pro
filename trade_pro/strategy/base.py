import logging
from abc import abstractmethod
from typing import Any

import numpy as np
import pandas as pd

from trade_pro.strategy.utils import fetch_candles, get_data, update_data

logger = logging.getLogger(__name__)


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
        start_live_index: int = -1,
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
        self.peak_balance = self.initial_balance
        self.max_drawdown = 0
        self.trades = []
        self.mode = None

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
        histo_data = {timeframe: get_data(self.symbol, timeframe) for timeframe in self.timeframes}
        data = self.compute_indicators(histo_data)
        self.mode = mode
        if self.mode == "backtest":
            self.backtest(data)
        elif self.mode == "live":
            self.live(data, histo_data)

    def live(self, data: pd.DataFrame, histo_data: dict[str, pd.DataFrame]) -> None:
        """run trading strategy"""
        entry_price = 0
        entry_time = pd.NaT
        units = 0
        while True:
            new_dfs = {
                timeframe: update_data(
                    histo_data[timeframe], fetch_candles(self.symbol, timeframe, 50)
                )
                for timeframe in self.timeframes
            }
            data = self.compute_indicators(new_dfs)

            row = data.iloc[self.start_live_index]
            if self.entry_condition(data, index=self.start_live_index):
                entry_price, entry_time, units = self.execute_entry(row)
            elif self.exit_condition(data, index=self.start_live_index):
                self.execute_exit(row, entry_price, entry_time, units)
            # wait_for_next_candle(self.main_timeframe)

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
        # self.generate_chart(close_prices, close_times)

    def execute_entry(
        self,
        row: pd.Series,
    ) -> tuple[float, pd.Timestamp, float]:
        entry_price = row["close"] * (1 + self.slippage + self.commission)
        units = self.balance / entry_price
        self.position = True
        entry_time = row.name
        msg = f"📈 [ENTRY] {self.symbol} {entry_time} @ {entry_price:.2f}"
        if self.mode == "backtest":
            logger.info(msg)
        if self.mode == "live":
            self.bot.send_telegram_message(msg)
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
        return_pct = pnl / (units * entry_price) * 100
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
        self.peak_balance = max(self.peak_balance, self.balance)
        drawdown = (self.peak_balance - self.balance) / self.peak_balance
        self.max_drawdown = max(self.max_drawdown, drawdown)
        self.position = False
        msg = (
            f"📉 [LONG EXIT] {self.symbol} Time: {exit_time} Price: ${exit_price:.2f}."
            f"PnL: ${pnl:.2f} | Return: {return_pct:.2f}%"
        )
        if self.mode == "backtest":
            logger.info(msg)
        if self.mode == "run":
            self.bot.send_telegram_message(msg)

    def resume_backtest(self, trades: list[dict[str, Any]]):
        trade_df = pd.DataFrame(trades)
        logger.info("\nTrade Summary:")
        logger.info(trade_df)

        # Performance Metrics
        returns = [t["return_pct"] for t in trades]
        wins = trade_df[trade_df["pnl"] > 0]
        losses = trade_df[trade_df["pnl"] <= 0]
        total_wins = wins["pnl"].sum()
        total_losses = abs(losses["pnl"].sum())
        value_weighted_win_rate = (
            total_wins / (total_wins + total_losses) * 100 if (total_wins + total_losses) > 0 else 0
        )
        win_rate = len(wins) / len(trade_df) * 100
        profit_factor = total_wins / total_losses if total_losses != 0 else float("inf")
        max_drawdown = (trade_df["pnl"].cumsum().cummax() - trade_df["pnl"].cumsum()).max()
        total_pnl = trade_df["pnl"].sum()
        sharpe_like = float("nan")
        if len(returns) > 0:
            sharpe_like = np.mean(returns) / (np.std(returns) + 1e-9)  # avoid div by zero

        logger.info("\nStats:")
        logger.info(f"Total Trades: {len(trade_df)}")
        logger.info(f"Win Trades: {len(wins)}")
        logger.info(f"Lose Trades: {len(losses)}")
        logger.info(f"Max win: ${wins['pnl'].max():.2f}")
        logger.info(f"Max lose: ${losses['pnl'].min():.2f}")
        logger.info(f"Win Rate (Count-Based): {win_rate:.2f}%")
        logger.info(f"Win Rate (PnL-Weighted): {value_weighted_win_rate:.2f}%")
        logger.info(f"Profit Factor: {profit_factor:.2f}")
        logger.info(f"Sharpe-like Ratio (return_pct/std): {sharpe_like:.2f}")
        logger.info(f"Max Drawdown: ${max_drawdown:.2f}")
        logger.info(f"Total PnL: ${total_pnl:.2f}")
        logger.info(f"Final Balance: ${(total_pnl + self.initial_balance):.2f}")
