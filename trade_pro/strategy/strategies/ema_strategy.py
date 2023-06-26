import logging
from dataclasses import dataclass
from typing import Any

import talib as ta
from numpy.typing import NDArray

from trade_pro.config import AsyncClient
from trade_pro.strategy.base import Base

logger = logging.getLogger(__name__)


@dataclass
class EmaStrategy(Base):
    """_summary_

    Args:
        Base (_type_): _description_

    Returns:
        _type_: _description_
    """

    tema_fast_timeperiod: int = 10
    tema_slow_timeperiod: int = 50
    dema_timeperiod: int = 200

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
        dema = ta.DEMA(close_prices, timeperiod=self.dema_timeperiod)
        tema_fast = ta.TEMA(close_prices, timeperiod=self.tema_fast_timeperiod)
        tema_slow = ta.TEMA(close_prices, timeperiod=self.tema_slow_timeperiod)
        return close_prices, dema, tema_fast, tema_slow

    def entry_condition(self, klines: dict[str, Any], *, index: int = -1) -> bool:
        """Buy when the price is higher than the dema indicator and the fast tema
        crosses the slow tema upwards

        Args:
            klines (dict[str, Any]): contains the candlesticks information:
            opening price, closing price, high price, low price, opening and
            closing timestamp, volume, etc...
            index (int, optional): position in the numpy data array. Defaults to -1.

        Returns:
            bool: entry or not to the market
        """

        close_prices, dema, tema_fast, tema_slow = self.indicators(klines)

        return (
            not self.position_held
            and close_prices[index] > dema[index]
            and tema_fast[index - 1] < tema_slow[index] < tema_fast[index]
        )

    def exit_condition(self, klines: dict[str, Any], *, index: int = -1) -> bool:
        """Sell when the price is higher than the dema indicator and the fast tema
        crosses the slow tema downwards

        Args:
            klines (dict[str, Any]): contains the candlesticks information:
            opening price, closing price, high price, low price, opening and
            closing timestamp, volume, etc...
            index (int, optional): position in the numpy data array. Defaults to -1.

        Returns:
            bool: exit or not from the market
        """

        close_prices, dema, tema_fast, tema_slow = self.indicators(klines)

        return self.position_held and (
            self.stop_loss_condition(klines, index=index)
            or (
                close_prices[index] > dema[index]
                and tema_fast[index] < tema_slow[index] < tema_fast[index - 1]
            )
        )


# max 6329.455103337635
init = EmaStrategy(
    init_balance=2000,
    percentage_to_invest=100,
    stop_loss=5,
    symbol="BTCUSDT",
    start_time_back_testing="3 years ago UTC",
    start_time_strategy="9 days ago UTC",
    # kline_interval=AsyncClient.KLINE_INTERVAL_1HOUR,
    # kline_interval=AsyncClient.KLINE_INTERVAL_30MINUTEs,
    kline_interval=AsyncClient.KLINE_INTERVAL_1MINUTE,
)
