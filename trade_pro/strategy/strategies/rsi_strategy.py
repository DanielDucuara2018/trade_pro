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
    """_summary_

    Args:
        Base (_type_): _description_

    Returns:
        _type_: _description_
    """

    rsi_timeperiod: int = 2
    ema_timeperiod: int = 200

    def indicators(self, klines: dict[str, Any]) -> tuple[NDArray]:
        """calculates the indicators used in buying and selling

        Args:
            klines (dict[str, Any]): contains the candlesticks information:
            opening price, closing price, high price, low price, opening and
            closing timestamp, volume, etc...

        Returns:
            tuple[Any]: set of indicators
        """
        close_prices = self.close_prices(klines)
        rsi_values = ta.RSI(close_prices, timeperiod=self.rsi_timeperiod)
        ema = ta.EMA(close_prices, timeperiod=self.ema_timeperiod)
        return close_prices, rsi_values, ema

    def entry_condition(self, klines: dict[str, Any], *, index: int = -1) -> bool:
        """Buy when price is above the ema and the rsi indicator crosses upwards
        the oversold line of 10

        Args:
            klines (dict[str, Any]): contains the candlesticks information:
            opening price, closing price, high price, low price, opening and
            closing timestamp, volume, etc...
            index (int, optional): position in the numpy data array. Defaults to -1.

        Returns:
            bool: entry or not to the market
        """

        close_prices, rsi_values, ema = self.indicators(klines)

        return (
            not self.position_held
            and close_prices[index] > ema[index]
            and rsi_values[index - 1] < 10 < rsi_values[index]
        )

    def exit_condition(self, klines: dict[str, Any], *, index: int = -1) -> bool:
        """sells when price is above the ema and the rsi indicator crosses down
        the overbought line of 90

        Args:
            klines (dict[str, Any]): contains the candlesticks information:
            opening price, closing price, high price, low price, opening and
            closing timestamp, volume, etc...
            index (int, optional): position in the numpy data array. Defaults to -1.

        Returns:
            bool: exit or not to the market
        """

        close_prices, rsi_values, ema = self.indicators(klines)

        return self.position_held and (
            self.stop_loss_condition(klines, index=index)
            or (
                close_prices[index] > ema[index]
                and rsi_values[index] < 90 < rsi_values[index - 1]
            )
        )


# max 6329.455103337635
init = RsiStrategy(
    init_balance=2000,
    percentage_to_invest=100,
    stop_loss=5,
    symbol="BTCUSDT",
    start_time_back_testing="3 years ago UTC",
    start_time_strategy="9 days ago UTC",
    kline_interval=AsyncClient.KLINE_INTERVAL_1HOUR,
    # kline_interval=AsyncClient.KLINE_INTERVAL_1MINUTE,
)
