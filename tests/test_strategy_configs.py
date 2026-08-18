"""
Regression test: every shipped strategy config must load and run a real
backtest without raising, and must produce its own chart image — distinct
from every other config's.

This exists because several of these config/strategy pairs have, at various
points, been silently broken end-to-end (a config missing the "strategy"
wrapper the runner requires, a strategy method overridden with an incompatible
signature, a config referencing constructor kwargs that belong to a different
class) with nothing in the test suite catching it — see git history around
MultiEmaStrategy and rsi_strategy_btcusdt.json.

It also catches a real chart-naming bug: Base.generate_chart() names its PNG
output `{symbol}_{class_name}_*.png` by default. Several strategies (MASStrategy
alone has 8 configs) ship multiple parameter sets for the *same* class + symbol
— without run_label (see base.py), every one of those configs silently
overwrites the previous one's saved chart on disk, and nothing would ever
notice. This test forces each config to use its own config-name-based chart
filename (matching what runner.py does for real CLI runs) and asserts the
result is a freshly-written, uniquely-named file.

Rather than run every strategy through the CLI, this maps each config file to
its strategy class explicitly (config files don't self-describe their class)
and instantiates + backtests it directly.
"""

import time

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
from trade_pro.strategy.utils import IMAGES_DIR, load_strategy_config

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


# Chart paths claimed so far across this whole parametrized test run, so a
# naming collision between two *different* configs is caught immediately
# instead of one silently overwriting the other's PNG on disk.
_CLAIMED_IMAGE_PATHS: dict = {}


def _chart_paths(symbol: str, label: str) -> tuple:
    stem = f"{symbol.replace('/', '')}_{label}"
    return IMAGES_DIR / f"{stem}_strategy.png", IMAGES_DIR / f"{stem}_equity_curve.png"


@pytest.mark.parametrize("config_name", sorted(CONFIG_TO_CLASS))
def test_strategy_config_runs_end_to_end(config_name):
    config = load_strategy_config(config_name)
    assert "strategy" in config, f"{config_name}.json has no 'strategy' section"

    cls = CONFIG_TO_CLASS[config_name]
    kwargs = _build_strategy_kwargs(config_name, config)

    strategy = cls(**kwargs)
    # Give this config its own chart filename (same as runner.py does for a
    # real CLI run) — otherwise every config sharing this class + symbol would
    # write to the exact same PNG, and this test could pass for each one
    # individually while quietly leaving only the last run's chart on disk.
    strategy.run_label = config_name

    price_chart_path, equity_curve_path = _chart_paths(strategy.symbol, config_name)

    # No other config should already be using this exact path — if one is,
    # run_label isn't actually making filenames unique per config.
    for path in (price_chart_path, equity_curve_path):
        assert path not in _CLAIMED_IMAGE_PATHS or _CLAIMED_IMAGE_PATHS[path] == config_name, (
            f"{path} would collide between configs "
            f"{_CLAIMED_IMAGE_PATHS.get(path)!r} and {config_name!r}"
        )
        _CLAIMED_IMAGE_PATHS[path] = config_name
        # If a chart from a previous run/session is already sitting at this
        # path, remove it first — "PASSED" below must mean *this* run
        # (re)generated it, not that it found something already there.
        path.unlink(missing_ok=True)

    before = time.time()
    strategy.run(Mode.BACKTEST)  # must not raise

    # A config that can never produce a valid check_config() is also a bug —
    # it would fail identically (and silently, for OPTIMIZATION mode) in
    # production.
    assert strategy.check_config()

    if len(strategy.trades) == 0:
        pytest.skip(f"{config_name} produced zero trades over the test period — no chart to check")

    for path in (price_chart_path, equity_curve_path):
        assert path.exists(), f"{config_name} did not (re)generate {path}"
        assert path.stat().st_mtime >= before, f"{path} exists but wasn't regenerated by this run"
