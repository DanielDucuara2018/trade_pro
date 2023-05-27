import logging
from dataclasses import dataclass
from typing import Any

import talib as ta
from numpy.typing import NDArray

from trade_pro.config import AsyncClient
from trade_pro.strategy.base import Base

logger = logging.getLogger(__name__)


@dataclass
class StochasticStrategy(Base):
    """Strategy using Stocastic indicator and RSI indicator

    Raises:
        Exception: _description_

    Returns:
        _type_: _description_
    """

    rsi_timeperiod: int = 14
    ema_timeperiod: int = 200

    def indicators(self, klines: dict[str, Any]) -> tuple[NDArray]:
        """_summary_

        Args:
            klines (_type_): _description_

        Returns:
            tuple[Any]: _description_
        """
        close_prices = self.close_prices(klines)
        high_prices = self.high_prices(klines)
        low_prices = self.low_prices(klines)

        rsi_values = ta.RSI(close_prices, timeperiod=self.rsi_timeperiod)
        slowk, slowd = ta.STOCH(high_prices, low_prices, close_prices)
        ema = ta.EMA(close_prices, timeperiod=self.ema_timeperiod)
        return close_prices, ema, rsi_values, slowk, slowd

    def entry_condition(self, klines: dict[str, Any], *, index: int = -1) -> bool:
        """Buy when stocastic indicator crosses each other in oversold zone (less than 20)
        and rsi indicator crosses above 50 level

        Args:
            klines (Any): _description_
            index (int, optional): _description_. Defaults to -1.

        Returns:
            bool: entry_condition
        """

        close_prices, ema, rsi_values, slowk, slowd = self.indicators(klines)

        return (
            not self.position_held
            and close_prices[index] > ema[index]
            and slowk[index] < 20
            and slowd[index] < 20
            and slowk[index - 1] < slowd[index] < slowk[index]
            and rsi_values[index - 1] < 50 < rsi_values[index]
        )

    def exit_condition(self, klines: dict[str, Any], *, index: int = -1) -> bool:
        """Sell when stocastic indicator cross each other in overbought zone (more than 80)
        and rsi indicator crosses below 50 level

        Args:
            klines (_type_): _description_
            index (int, optional): _description_. Defaults to -1.

        Returns:
            bool: exit_condition
        """

        (
            close_prices,
            ema,
            rsi_values,
            slowk,
            slowd,
        ) = self.indicators(klines)

        return self.position_held and (
            # self.stop_loss_condition(klines, index=index)
            (
                close_prices[index] > ema[index]
                and slowk[index] > 80
                and slowd[index] > 80
                and slowk[index] < slowd[index] < slowk[index - 1]
                and rsi_values[index] < 50 < rsi_values[index - 1]
            )
        )


init = StochasticStrategy(
    init_balance=2000,
    percentage_to_invest=100,
    stop_loss=1,
    symbol="BTCUSDT",
    start_time_back_testing="3 year ago UTC",
    start_time_strategy="9 days ago UTC",
    kline_interval=AsyncClient.KLINE_INTERVAL_1HOUR,
)
