import logging
from dataclasses import dataclass
from typing import Any

import talib as ta
from numpy.typing import NDArray

from trade_pro.config import AsyncClient
from trade_pro.strategy.base import Base

logger = logging.getLogger(__name__)


@dataclass
class RsiStrategy(Base):

    rsi_timeperiod: int = 14
    ema_timeperiod: int = 200

    def indicators(self, klines: dict[str, Any]) -> tuple[NDArray]:
        """_summary_

        Args:
            klines (dict[str, Any]): _description_

        Returns:
            tuple[Any]: _description_
        """
        close_prices = self.close_prices(klines)
        rsi_values = ta.RSI(close_prices, timeperiod=self.rsi_timeperiod)
        ema = ta.EMA(close_prices, timeperiod=self.ema_timeperiod)
        macd, macd_signal, _ = ta.MACD(close_prices)
        return close_prices, rsi_values, macd, macd_signal, ema

    def entry_condition(self, klines: dict[str, Any], *, index: int = -1) -> bool:
        """_summary_

        Args:
            klines (dict[str, Any]): _description_
            index (int, optional): _description_. Defaults to -1.

        Returns:
            bool: _description_
        """

        close_prices, rsi_values, macd, macd_signal, ema = self.indicators(klines)

        return (
            not self.position_held
            # and close_prices[index] > ema[index]
            and rsi_values[index - 1] < 30 < rsi_values[index]
            and macd[index - 1] < macd_signal[index] < macd[index]
        )

    def exit_condition(self, klines: dict[str, Any], *, index: int = -1) -> bool:
        """_summary_

        Args:
            klines (dict[str, Any]): _description_
            index (int, optional): _description_. Defaults to -1.

        Returns:
            bool: _description_
        """

        close_prices, rsi_values, macd, macd_signal, ema = self.indicators(klines)

        return self.position_held and (
            # self.stop_loss_condition(klines, index=index)
            (
                # close_prices[index] > ema[index]
                rsi_values[index] < 70 < rsi_values[index - 1]
                and macd[index] < macd_signal[index] < macd[index - 1]
            )
        )


init = RsiStrategy(
    init_balance=2000,
    percentage_to_invest=100,
    stop_loss=5,
    symbol="BTCUSDT",
    start_time_back_testing="3 years ago UTC",
    start_time_strategy="9 days ago UTC",
    kline_interval=AsyncClient.KLINE_INTERVAL_1HOUR,
)
