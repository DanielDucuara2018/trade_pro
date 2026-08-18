"""
Regression test: every shipped strategy config must load and run a real
backtest without raising.

This exists because several of these config/strategy pairs have, at various
points, been silently broken end-to-end (a config missing the "strategy"
wrapper the runner requires, a strategy method overridden with an incompatible
signature, a config referencing constructor kwargs that belong to a different
class) with nothing in the test suite catching it — see git history around
MultiEmaStrategy and rsi_strategy_btcusdt.json.

Rather than run every strategy through the CLI, this maps each config file to
its strategy class explicitly (config files don't self-describe their class)
and instantiates + backtests it directly.
"""

import numpy as np
import pytest

from trade_pro.strategy.base import Mode
from trade_pro.strategy.strategies.bollinger_bands_strategy import BollingerBandsStrategy
from trade_pro.strategy.strategies.ema_atr_reversal_strategy import EmaAtrReversalStrategy
from trade_pro.strategy.strategies.ema_strategy import EMAStrategy
from trade_pro.strategy.strategies.ma_crossover_strategy import MACrossoverStrategy
from trade_pro.strategy.strategies.macd_slope_strategy import MACDSlopeStrategy
from trade_pro.strategy.strategies.macd_strategy import MACDStrategy
from trade_pro.strategy.strategies.mas_strategy import MASStrategy
from trade_pro.strategy.strategies.multi_ema_strategy import MultiEmaStrategy
from trade_pro.strategy.strategies.pi_cycle_strategy import PiCycleStrategy
from trade_pro.strategy.strategies.rsi_strategy import RSIStrategy
from trade_pro.strategy.strategies.stochastic_strategy import StochasticStrategy
from trade_pro.strategy.strategies.volume_mas_strategy import VolumeMASStrategy
from trade_pro.strategy.strategies.vwap_strategy import VWAPStrategy
from trade_pro.strategy.utils import load_strategy_config

# config filename (without .json) -> strategy class
CONFIG_TO_CLASS = {
    "bollinger_bands_strategy": BollingerBandsStrategy,
    "ema_atr_reversal_strategy_btcusdt": EmaAtrReversalStrategy,
    "ema_atr_reversal_strategy_btcusdt_2": EmaAtrReversalStrategy,
    "ema_atr_reversal_strategy_btcusdt_3": EmaAtrReversalStrategy,
    "ema_strategy_btcusdt": EMAStrategy,
    "ema_strategy_ethusdt": EMAStrategy,
    "ma_crossover_strategy": MACrossoverStrategy,
    "macd_slope_strategy": MACDSlopeStrategy,
    "macd_slope_strategy_btcusdt": MACDSlopeStrategy,
    "macd_slope_strategy_ethusdt": MACDSlopeStrategy,
    "macd_slope_strategy_linkusdt": MACDSlopeStrategy,
    "macd_slope_strategy_solusdt": MACDSlopeStrategy,
    "macd_strategy_btcusdt": MACDStrategy,
    "macd_strategy_ethusdt": MACDStrategy,
    "mas_strategy_btcusdt": MASStrategy,
    "mas_strategy_btcusdt_2": MASStrategy,
    "mas_strategy_btcusdt_3": MASStrategy,
    "mas_strategy_btcusdt_4": MASStrategy,
    "mas_strategy_btcusdt_5": MASStrategy,
    "mas_strategy_btcusdt_6": MASStrategy,
    "mas_strategy_ethusdt": MASStrategy,
    "mas_strategy_ethusdt_2": MASStrategy,
    "multi_ema_strategy_btcusdt": MultiEmaStrategy,
    "pi_cycle_strategy_btcusdt": PiCycleStrategy,
    "rsi_strategy": RSIStrategy,
    "rsi_strategy_btcusdt": RSIStrategy,
    "stochastic_strategy_btcusdt": StochasticStrategy,
    "stochastic_strategy_btcusdt_2": StochasticStrategy,
    "stochastic_strategy_ethusdt": StochasticStrategy,
    "test_standard_opti": MACDSlopeStrategy,  # optimization-only template, see below
    "volume_mas_strategy_btcusdt": VolumeMASStrategy,
    "volume_mas_strategy_btcusdt_2": VolumeMASStrategy,
    "volume_mas_strategy_ethusdt": VolumeMASStrategy,
    "volume_mas_strategy_solusdt": VolumeMASStrategy,
    "vwap_strategy_btcusdt": VWAPStrategy,
}


def _build_strategy_kwargs(config_name: str, config: dict) -> dict:
    """Return the kwargs to instantiate this config's strategy with.

    A handful of configs (currently just test_standard_opti.json) are
    optimization-only templates: their "strategy" section intentionally omits
    parameters that only get filled in per-trial from "optimization.variables"
    (e.g. macd_fast/macd_slow/macd_signal). To smoke-test those too, fill any
    such gap with the midpoint of that variable's [low, high] range.
    """
    kwargs = dict(config["strategy"])
    optimization_variables = config.get("optimization", {}).get("variables", {})
    for param, bounds in optimization_variables.items():
        if param not in kwargs:
            kwargs[param] = type(bounds["low"])(np.mean([bounds["low"], bounds["high"]]))
    return kwargs


@pytest.mark.parametrize("config_name", sorted(CONFIG_TO_CLASS))
def test_strategy_config_runs_end_to_end(config_name):
    config = load_strategy_config(config_name)
    assert "strategy" in config, f"{config_name}.json has no 'strategy' section"

    cls = CONFIG_TO_CLASS[config_name]
    kwargs = _build_strategy_kwargs(config_name, config)

    strategy = cls(**kwargs)
    strategy.run(Mode.BACKTEST)  # must not raise

    # A config that can never produce a valid check_config() is also a bug —
    # it would fail identically (and silently, for OPTIMIZATION mode) in
    # production.
    assert strategy.check_config()
