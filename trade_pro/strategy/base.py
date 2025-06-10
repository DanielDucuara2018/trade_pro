import asyncio
import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray
import pandas as pd


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
        position: bool = True,
        commission: float = 0.0004,
        slippage: float = 0.0005,
        # percentage_to_invest: int,
        # stop_loss: int,
        # start_time_back_testing: str,
        # start_time_strategy: str,
        # kline_interval: str,
        # wins: int = 0,
        # losses: int = 0,
        # buy_prices: list[float] = field(default_factory=list),
        # sell_prices: list[float] = field(default_factory=list),
        # bougth_in_stop_loss: bool = False,
        # price_in_stop_loss: int = 0,
    ):
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.position = position
        self.commission = commission
        self.slippage = slippage

        self.balance = self.initial_balance
        self.peak_balance = self.initial_balance
        self.max_drawdown = 0
        self.trades = []

    @abstractmethod
    def indicators(self, df: pd.DataFrame, *, df_high: pd.DataFrame | None = None) -> pd.DataFrame:
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


    def generate_chart(self, close_prices: NDArray, close_times: NDArray) -> None:
        pass


    def run(self, df: pd.DataFrame, *, index: int = -1) -> None:
        """run trading strategy"""
        df_1h = get_data(self.symbol, TIMEFRAME_1H)
        df_1d = get_data(self.symbol, TIMEFRAME_1D)

        df = self.indicators(df_1h, df_high=df_1d)

        # self.balance = self.initial_balance
        # peak_balance = self.initial_balance
        # max_drawdown = 0
        # trades = []

        # bot = TelegramBot(bot_token="your_token", chat_id="your_chat_id")
        # msg = "Running live strategy"
        # bot.send_telegram_message(msg)
        # logger.info(msg)
        entry_price = 0
        units = 0
        while True:
            df_new, df_1d_new = (
                fetch_candles(self.symbol, TIMEFRAME_1H, 50),
                fetch_candles(self.symbol, TIMEFRAME_1D, 50),
            )
            df, df_1d = update_data(df, df_new), update_data(df_1d, df_1d_new)
            df = self.indicators(df,df_high=df_1d)

            row = df.iloc[index]
            # prev = df.iloc[-2]
            # prev2 = df.iloc[-3]

            # if np.isnan(row["ATR_MA"]):
            #     continue

            # enter_long = (
            #     not position
            #     and prev2["SPREAD_SIGN"] == -1
            #     and prev["SPREAD_SIGN"] == -1
            #     and row["SPREAD_SIGN"] == 1
            #     and row["RSI"] < rsi_threshold
            #     and row["MACD"] > row["MACD_SIGNAL"]
            #     # and row['close'] < row['BB_LOWER']
            #     # and row['ADX'] > ADX_THRESHOLD
            #     # and row["close"] > row["EMA_FAST"]
            #     # and row["ATR"] > row["ATR_MA"]
            #     and row["BULLISH_TREND"]
            # )

            # exit_long = position and (
            #     prev2["SPREAD_SIGN"] == 1 and prev["SPREAD_SIGN"] == 1 and row["SPREAD_SIGN"] == -1
            #     # or (row['RSI'] > RSI_EXIT)
            #     # or (row['MACD'] < row['MACD_SIGNAL'])
            # )

            # --- Entry Conditions ---
            if self.entry_condition(df, index=index):
                entry_price, entry_time, units = self.execute_entry(row)

                # entry_price = row["close"] * (1 + self.slippage + self.commission)
                # units = balance / entry_price
                # self.position = True
                # entry_time = row.name
                # msg = f"📈 [ENTRY] {self.symbol} {entry_time} @ {entry_price:.2f}"
                # logger.info(msg)
                # bot.send_telegram_message(msg)
                # # trailing_stop = row['close'] - atr_trail_mult * row['ATR_MA']

            # --- Exit Conditions ---
            elif self.exit_condition(df,index=index):
                units = self.execute_exit(row, entry_price, entry_time, units)
                # elif position and trailing_stop is not None:
                #     trailing_stop = max(trailing_stop, row['close'] - atr_trail_mult * row['ATR_MA'])
                #     if row['close'] < trailing_stop:
                # exit_price = row["close"] * (1 - self.slippage - self.commission)
                # pnl = (exit_price - entry_price) * units
                # exit_time = row.name
                # return_pct = pnl / (units * entry_price) * 100
                # trades.append(
                #     {
                #         "entry_time": entry_time,
                #         "exit_time": exit_time,
                #         "entry_price": entry_price,
                #         "exit_price": exit_price,
                #         "pnl": pnl,
                #         "return_pct": return_pct,
                #         "old_balance": balance,
                #         "new_balance": balance + pnl,
                #     }
                # )
                # balance += pnl
                # peak_balance = max(peak_balance, balance)
                # drawdown = (peak_balance - balance) / peak_balance
                # max_drawdown = max(max_drawdown, drawdown)
                # self.position = False
                # units = 0
                # msg = (
                #     f"📉 [LONG EXIT] {self.symbol} Time: {exit_time} Price: ${exit_price:.2f}\n"
                #     f"PnL: ${pnl:.2f} | Return: {return_pct:.2f}%"
                # )
                # logger.info(msg)
                # bot.send_telegram_message(msg)

            wait_for_next_candle(TIMEFRAME_1H)

    def back_testing(self, *, index: int = 0) -> None:
        """run back testing strategy"""

        df_1h = get_data(self.symbol, TIMEFRAME_1H)
        df_1d = get_data(self.symbol, TIMEFRAME_1D)

        df = self.indicators(df_1h, df_high=df_1d)

        # balance = self.initial_balance
        # peak_balance = self.initial_balance
        # max_drawdown = 0
        # trades = []
        # trailing_stop = None

        # --- Backtest Logic ---
        entry_price = 0
        units = 0
        for i in range(index, len(df)):
            row = df.iloc[i]

            # --- Entry Conditions ---
            if self.entry_condition(df, index=i):
                entry_price, entry_time, units = self.execute_entry(row, mode="backtest")
                # entry_price = row["close"] * (1 + self.slippage + self.commission)
                # units = balance / entry_price
                # self.position = True
                # entry_time = row.name
                # # if mode == "backtest":
                # msg = f"📈 [ENTRY] {self.symbol} {entry_time} @ {entry_price:.2f}"
                # logger.info(msg)
                # # trailing_stop = row['close'] - atr_trail_mult * row['ATR_MA']

            # --- Exit Conditions ---
            elif self.exit_condition(df,index=i):
                self.execute_exit(row, entry_price, entry_time, units, mode="backtest")
                # # elif position and trailing_stop is not None:
                # #     trailing_stop = max(trailing_stop, row['close'] - atr_trail_mult * row['ATR_MA'])
                # #     if row['close'] < trailing_stop:
                # exit_price = row["close"] * (1 - self.slippage - self.commission)
                # pnl = (exit_price - entry_price) * units
                # exit_time = row.name
                # return_pct = pnl / (units * entry_price) * 100
                # # if mode == "backtest":
                # trades.append(
                #     {
                #         "entry_time": entry_time,
                #         "exit_time": exit_time,
                #         "entry_price": entry_price,
                #         "exit_price": exit_price,
                #         "pnl": pnl,
                #         "return_pct": return_pct,
                #         "old_balance": balance,
                #         "new_balance": balance + pnl,
                #     }
                # )
                # balance += pnl
                # peak_balance = max(peak_balance, balance)
                # drawdown = (peak_balance - balance) / peak_balance
                # max_drawdown = max(max_drawdown, drawdown)
                # self.position = False
                # units = 0
                # msg = (
                #     f"📉 [LONG EXIT] {self.symbol} Time: {exit_time} Price: ${exit_price:.2f}\n"
                #     f"PnL: ${pnl:.2f} | Return: {return_pct:.2f}%"
                # )
                # logger.info(msg)
                # bot.send_telegram_message(msg)
        # self.generate_chart(close_prices, close_times)

    def execute_entry(self, row: pd.Series, *, mode: str = "run") -> tuple[float, pd.Timestamp, float]:
        entry_price = row["close"] * (1 + self.slippage + self.commission)
        units = self.balance / entry_price
        self.position = True
        entry_time = row.name
        msg = f"📈 [ENTRY] {self.symbol} {entry_time} @ {entry_price:.2f}"
        if mode == "backtest":
            logger.info(msg)
        if mode == "run":
            self.bot.send_telegram_message(msg)
        return entry_price, entry_time, units
    

    def execute_exit(
        self, 
        row: pd.Series, 
        entry_price: float, 
        entry_time: pd.Timestamp, 
        units: float,
        *, 
        mode: str = "run"
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
        units = 0
        msg = (
            f"📉 [LONG EXIT] {self.symbol} Time: {exit_time} Price: ${exit_price:.2f}\n"
            f"PnL: ${pnl:.2f} | Return: {return_pct:.2f}%"
        )
        if mode == "backtest":
            logger.info(msg)
        if mode == "run":
            self.bot.send_telegram_message(msg)
        return units

        # trailing_stop = row['close'] - atr_trail_mult * row['ATR_MA']

        # # initialise the client
        # klines = await self.get_historical_klines(self.start_time_back_testing)
        # close_prices = self.close_prices(klines)
        # # close_times = self.close_times(klines)

        # investment = 0
        # currency_amount = 0
        # for i in range(len(close_prices)):
        #     last_price = close_prices[i]
        #     if self.entry_condition(klines, index=i):
        #         investment, currency_amount = self.buy_position(last_price)
        #         self.buy_prices.append(last_price)
        #     elif self.exit_condition(klines, index=i):
        #         self.sell_position(last_price, investment, currency_amount)
        #         self.sell_prices.append(last_price)

        # logger.info("Buys: %s. Sells: %s.", len(self.buy_prices), len(self.sell_prices))
        # logger.info("Wins: %s. Losses: %s.", self.wins, self.losses)
        # logger.info("Win rate: %s.", (self.wins / (self.wins + self.losses)) * 100)

        # logger.info("Final Balance: %s.", self.available_balance)
        # logger.info("ROI: %s.", (self.available_balance / self.init_balance) * 100)

        # if self.position_held:
        #     logger.info("Trading operation in progress.")
        # else:
        #     logger.info(
        #         "Profit from algorithm: %s.", self.available_balance - self.init_balance
        #     )

        
