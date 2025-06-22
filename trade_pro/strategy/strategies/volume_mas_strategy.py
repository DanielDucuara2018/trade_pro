import pandas as pd

from trade_pro.strategy.strategies.mas_strategy import MASStrategy


class VolumeMASStrategy(MASStrategy):
    def __init__(
        self,
        symbol: str,
        initial_balance: float,
        timeframes: list[str],
        start_backtest_index: int,
        fast: float,
        slow: float,
        rsi_period: float,
        rsi_threshold: float,
        macd_fast: float,
        macd_slow: float,
        macd_signal: float,
        trend_sma_period: float,
        volume_ma_period: float,
    ):
        super().__init__(
            symbol,
            initial_balance,
            timeframes,
            start_backtest_index,
            fast,
            slow,
            rsi_period,
            rsi_threshold,
            macd_fast,
            macd_slow,
            macd_signal,
            trend_sma_period,
        )
        self.volume_ma_period = volume_ma_period

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """calculates the indicators used in buying and selling"""

        # get data
        df_1h = super().compute_indicators(data)

        # --- Volume MA ---
        df_1h["VOLUME_MA"] = df_1h["volume"].rolling(self.volume_ma_period).mean()

        return df_1h

    def entry_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        """Buy when the price is higher than the dema indicator and the fast tema
        crosses the slow tema upwards."""

        row = df.iloc[index]

        return super().entry_condition(df, index=index) and row["volume"] > row["VOLUME_MA"]
