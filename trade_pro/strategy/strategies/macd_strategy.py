import logging
from dataclasses import dataclass
from typing import Any

import talib as ta
from numpy.typing import NDArray

from trade_pro.config import AsyncClient
from trade_pro.strategy.base import Base

logger = logging.getLogger(__name__)


@dataclass
class MacdStrategy(Base):
    """_summary_

    Args:
        Base (_type_): _description_

    Returns:
        _type_: _description_
    """

    rsi_timeperiod: int = 14
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
        macd, macd_signal, _ = ta.MACD(close_prices)
        return close_prices, rsi_values, macd, macd_signal, ema

    def entry_condition(self, klines: dict[str, Any], *, index: int = -1) -> bool:
        """Buy when rsi indicator crossover the 30 level and macd indicator crossover
        the signal macdBuy when the rsi indicator crosses the 30 level upwards and the
        macd indicator crosses the macd signal upwards.

        Args:
            klines (dict[str, Any]): contains the candlesticks information:
            opening price, closing price, high price, low price, opening and
            closing timestamp, volume, etc...
            index (int, optional): position in the numpy data array. Defaults to -1.

        Returns:
            bool: entry or not to the market
        """

        close_prices, rsi_values, macd, macd_signal, ema = self.indicators(klines)

        return (
            not self.position_held
            # and close_prices[index] > ema[index]
            and rsi_values[index - 1] < 30 < rsi_values[index]
            and macd[index - 1] < macd_signal[index] < macd[index]
        )

    def exit_condition(self, klines: dict[str, Any], *, index: int = -1) -> bool:
        """Buy when the rsi indicator crosses downwards the 70 level and the macd
        indicator crosses downwards the macd signal.

        Args:
            klines (dict[str, Any]): contains the candlesticks information:
            opening price, closing price, high price, low price, opening and
            closing timestamp, volume, etc...
            index (int, optional): position in the numpy data array. Defaults to -1.

        Returns:
            bool: exit or not from the market
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


init = MacdStrategy(
    init_balance=2000,
    percentage_to_invest=100,
    stop_loss=5,
    symbol="BTCUSDT",
    start_time_back_testing="3 years ago UTC",
    start_time_strategy="9 days ago UTC",
    kline_interval=AsyncClient.KLINE_INTERVAL_1HOUR,
)
