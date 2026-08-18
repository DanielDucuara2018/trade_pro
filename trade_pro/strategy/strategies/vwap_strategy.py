import pandas as pd

from trade_pro.strategy.base import Base


class VWAPStrategy(Base):
    """
    VWAP-based trading strategy using standard deviation bands.

    Entry Condition:
        - No open position.
        - Price crosses below VWAP from above.
        - Price is below yesterday’s VWAP (acting as resistance).

    Exit Condition:
        - Price hits dynamically calculated stop-loss (VWAP + std).
        - OR price hits dynamically calculated take-profit (VWAP - 2*std).

    Parameters:
        symbol (str): Trading pair (e.g., "BTCUSDT").
        initial_balance (float): Starting capital.
        timeframes (list[str]): Timeframes used (must include "1h").
        start_backtest_index (int): Index to begin backtest from.
        std_window (int): Rolling window for standard deviation.
        band_upper_multiplier (float): Multiplier for stop-loss band.
        band_lower_multiplier (float): Multiplier for take-profit band.
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float,
        timeframes: list[str],
        start_backtest_index: int,
        std_window: int,
        band_upper_multiplier: float,
        band_lower_multiplier: float,
    ):
        super().__init__(
            symbol, initial_balance, timeframes, start_backtest_index=start_backtest_index
        )
        self.std_window = std_window
        self.band_upper_multiplier = band_upper_multiplier
        self.band_lower_multiplier = band_lower_multiplier
        self.dynamic_stop_loss = 0
        self.dynamic_take_profit = 0

    def check_config(self) -> bool:
        return (
            self.std_window > 0
            and self.band_upper_multiplier > 0
            and self.band_lower_multiplier > 0
        )

    def compute_indicators(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """calculates the indicators used in buying and selling"""

        # get data
        df_1h = data["1h"]

        # VWAP calculation
        df_1h["pv"] = df_1h["close"] * df_1h["volume"]
        df_1h["cumulative_pv"] = df_1h["pv"].cumsum()
        df_1h["cumulative_volume"] = df_1h["volume"].cumsum()
        df_1h["vwap"] = df_1h["cumulative_pv"] / df_1h["cumulative_volume"]

        # Standard deviation and VWAP bands
        df_1h["std"] = df_1h["close"].rolling(window=self.std_window).std()
        df_1h["vwap_upper_1SD"] = df_1h["vwap"] + self.band_upper_multiplier * df_1h["std"]
        df_1h["vwap_lower_1SD"] = df_1h["vwap"] - self.band_upper_multiplier * df_1h["std"]
        df_1h["vwap_upper_2SD"] = df_1h["vwap"] + self.band_lower_multiplier * df_1h["std"]
        df_1h["vwap_lower_2SD"] = df_1h["vwap"] - self.band_lower_multiplier * df_1h["std"]

        # Yesterday's VWAP (used as fixed S/R level).
        # Computed causally per calendar day: an hourly candle on day D may only
        # see day D-1's *final* VWAP, never a value derived from data at or after
        # that candle. (Previously this took one scalar from near the end of the
        # entire dataset and broadcast it onto every historical row.)
        day = df_1h.index.normalize()
        daily_last_vwap = df_1h.groupby(day)["vwap"].last()
        df_1h["vwap_yesterday"] = day.map(daily_last_vwap.shift(1))

        return df_1h

    def entry_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        row = df.iloc[index]
        prev = df.iloc[index - 1]

        entry_signal = (
            not self.position
            and prev["close"] > prev["vwap"]
            and row["close"] < row["vwap"]
            and row["close"] < row["vwap_yesterday"]
        )

        if entry_signal:
            # Fix the stop/target at entry time — only recompute them when a new
            # trade is actually opened, not on every call (previously these were
            # overwritten from the *current* candle's VWAP bands every bar,
            # including while a trade was already open, so the "stop" drifted
            # with the market instead of staying fixed from entry).
            self.dynamic_stop_loss = row["vwap_upper_1SD"]
            self.dynamic_take_profit = row["vwap_lower_2SD"]

        return entry_signal

    def exit_condition(self, df: pd.DataFrame, *, index: int = 0) -> bool:
        row = df.iloc[index]

        return self.position and (
            row["high"] >= self.dynamic_stop_loss or row["low"] <= self.dynamic_take_profit
        )
