import asyncio
import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

from trade_pro.config import create_binance_client

logger = logging.getLogger(__name__)


@dataclass
class Base:

    init_balance: float
    percentage_to_invest: int
    stop_loss: int
    symbol: str
    start_time_back_testing: str
    start_time_strategy: str
    kline_interval: str

    wins: int = 0
    losses: int = 0
    position_held: bool = False
    buy_prices: list[float] = field(default_factory=list)
    sell_prices: list[float] = field(default_factory=list)
    bougth_in_stop_loss: bool = False
    price_in_stop_loss: int = 0

    def __post_init__(self):
        self.available_balance: int = self.init_balance

    def high_prices(self, klines: dict[str, Any]) -> NDArray:
        """_summary_

        Args:
            klines (dict[str, Any]): _description_

        Returns:
            NDArray: _description_
        """
        return np.array([float(kline[1]) for kline in klines])

    def high_prices(self, klines: dict[str, Any]) -> NDArray:
        """_summary_

        Args:
            klines (dict[str, Any]): _description_

        Returns:
            NDArray: _description_
        """
        return np.array([float(kline[2]) for kline in klines])

    def low_prices(self, klines: dict[str, Any]) -> NDArray:
        """_summary_

        Args:
            klines (dict[str, Any]): _description_

        Returns:
            NDArray: _description_
        """
        return np.array([float(kline[3]) for kline in klines])

    def close_prices(self, klines: dict[str, Any]) -> NDArray:
        """_summary_

        Args:
            klines (dict[str, Any]): _description_

        Returns:
            NDArray: _description_
        """
        return np.array([float(kline[4]) for kline in klines])

    def close_times(self, klines: dict[str, Any]) -> NDArray:
        """_summary_

        Args:
            klines (dict[str, Any]): _description_

        Returns:
            NDArray: _description_
        """
        return np.array(
            [datetime.fromtimestamp(float(kline[6] / 1000)) for kline in klines]
        )

    def get_buy_prices(self) -> NDArray:
        """_summary_

        Returns:
            NDArray: _description_
        """
        return np.array(self.buy_prices)

    def get_sell_prices(self) -> NDArray:
        """_summary_

        Returns:
            NDArray: _description_
        """
        return np.array(self.sell_prices)

    @abstractmethod
    def indicators(self, klines: dict[str, Any]) -> tuple[Any]:
        """_summary_

        Args:
            klines (dict[str, Any]): _description_

        Returns:
            tuple[Any]: _description_
        """
        pass

    @abstractmethod
    def entry_condition(self, klines: dict[str, Any], *, index: int = -1) -> bool:
        """_summary_

        Args:
            klines (dict[str, Any]): _description_
            index (int, optional): _description_. Defaults to -1.

        Returns:
            bool: _description_
        """
        pass

    @abstractmethod
    def exit_condition(self, klines: dict[str, Any], *, index: int = -1) -> bool:
        """_summary_

        Args:
            klines (dict[str, Any]): _description_
            index (int, optional): _description_. Defaults to -1.

        Returns:
            bool: _description_
        """
        pass

    def generate_chart(self, close_prices: NDArray, close_times: NDArray) -> None:
        """_summary_

        Args:
            close_prices (NDArray): _description_
            close_times (NDArray): _description_
        """

        title = f"{self.symbol} chart"
        # plt.title(title)
        # plt.xlabel("time")
        # plt.ylabel("usdt")
        # plt.plot(np_close_times, np_close_price)
        file_name = f"{self.symbol}_chart.png"
        # plt.savefig(file_name)

        _, ax = plt.subplots()
        ax.set_title(title)
        ax.set_xlabel("time")
        ax.set_ylabel("usdt")
        ax.plot(close_times, close_prices)
        ax.plot(close_times, self.get_buy_prices(), "g.")
        ax.plot(close_times, self.get_sell_prices(), "r.")
        plt.savefig(file_name)

    def stop_loss_condition(self, klines: dict[str, Any], *, index: int = -1) -> bool:
        """_summary_

        Args:
            klines (dict[str, Any]): _description_
            index (int, optional): _description_. Defaults to -1.

        Returns:
            bool: _description_
        """
        low_prices = self.low_prices(klines)
        high_prices = self.high_prices(klines)
        price_in_stop_loss = self.buy_prices[-1] * (1 - (self.stop_loss / 100))
        if condition := low_prices[index] < price_in_stop_loss < high_prices[index]:
            self.bougth_in_stop_loss = True
            self.price_in_stop_loss = price_in_stop_loss
        return condition

    def buy_position(self, last_price: float) -> tuple[float]:
        """_summary_

        Args:
            last_price (float): _description_

        Returns:
            tuple[float]: _description_
        """
        logger.info("buying at %s", last_price)
        money_to_investment = self.available_balance * (self.percentage_to_invest / 100)
        currency_amount = money_to_investment / last_price
        self.available_balance -= money_to_investment
        self.position_held = True
        logger.info(
            "bought %s at %s. Amount %s",
            money_to_investment,
            last_price,
            currency_amount,
        )
        return money_to_investment, currency_amount

    def sell_position(
        self, last_price: float, investment: float, currency_amount: float
    ) -> None:
        """_summary_

        Args:
            last_price (float): _description_
            investment (float): _description_
            currency_amount (float): _description_
        """
        logger.info("selling at %s", last_price)
        if self.bougth_in_stop_loss:
            logger.info(
                "selling at SL %s instead %s", self.price_in_stop_loss, last_price
            )
            last_price = self.price_in_stop_loss
            self.bougth_in_stop_loss = False

        sale = last_price * currency_amount
        earned = sale - investment
        if earned >= 0:
            self.wins += 1
        else:
            self.losses += 1
        self.available_balance += sale
        self.position_held = False
        logger.info(
            "Sold %s at %s. Earned %s. New balance %s",
            currency_amount,
            last_price,
            earned,
            self.available_balance,
        )

    async def get_historical_klines(self, start_time: str) -> dict[str, Any]:
        """_summary_

        Args:
            start_time (str): _description_

        Raises:
            Exception: _description_

        Returns:
            dict[str, Any]: _description_
        """
        client = await create_binance_client()
        try:
            return await client.get_historical_klines(
                self.symbol,
                self.kline_interval,
                start_time,
            )
        except:
            raise Exception
        finally:
            await client.close_connection()

    async def run(self) -> None:
        """run trading strategy"""
        investment = 0
        currency_amount = 0
        self.start_time_back_testing = "9 days ago UTC"
        while 1:
            klines = await self.get_historical_klines(self.start_time_strategy)
            close_prices = self.close_prices(klines)

            last_price = close_prices[-1]
            logger.info("Current price %s", last_price)
            if self.entry_condition(klines):
                investment, currency_amount = self.buy_position(last_price)
                self.buy_prices.append(last_price)
            elif self.exit_condition(klines):
                last_price = self.sell_position(last_price, investment, currency_amount)
                self.sell_prices.append(last_price)
            # else:
            #     logger.info("Nothing was bought or sold.")

            logger.info(
                "Buys: %s. Sells: %s.", len(self.buy_prices), len(self.sell_prices)
            )

            await asyncio.sleep(5)

    async def back_testing(self) -> None:
        """run back testing strategy"""
        # initialise the client
        klines = await self.get_historical_klines(self.start_time_back_testing)
        close_prices = self.close_prices(klines)
        # close_times = self.close_times(klines)

        investment = 0
        currency_amount = 0
        for i in range(len(close_prices)):
            last_price = close_prices[i]
            if self.entry_condition(klines, index=i):
                investment, currency_amount = self.buy_position(last_price)
                self.buy_prices.append(last_price)
            elif self.exit_condition(klines, index=i):
                self.sell_position(last_price, investment, currency_amount)
                self.sell_prices.append(last_price)

        logger.info("Buys: %s. Sells: %s.", len(self.buy_prices), len(self.sell_prices))
        logger.info("Wins: %s. Losses: %s.", self.wins, self.losses)
        logger.info("Win rate: %s.", (self.wins / (self.wins + self.losses)) * 100)

        logger.info("Final Balance: %s.", self.available_balance)
        logger.info("ROI: %s.", (self.available_balance / self.init_balance) * 100)

        if self.position_held:
            logger.info("Trading operation in progress.")
        else:
            logger.info(
                "Profit from algorithm: %s.", self.available_balance - self.init_balance
            )

        # self.generate_chart(close_prices, close_times)
