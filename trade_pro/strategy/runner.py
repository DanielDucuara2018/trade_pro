import logging

from trade_pro.strategy import get_module_class
from trade_pro.strategy.base import Mode
from trade_pro.strategy.optimization import run_optimization, run_walk_forward_optimization
from trade_pro.strategy.utils import load_strategy_config

logger = logging.getLogger(__name__)


def run(mode: str, strategy_name: str, file_name: str) -> None:
    """
    Run a trading strategy in different modes.

    Args:
        mode: 'backtest', 'live', or 'optimization'
        strategy_name: Name of the strategy class
        file_name: Config file name
    """
    logger.info("Loading strategy config %s", strategy_name)
    config = load_strategy_config(file_name)
    cls = get_module_class(strategy_name)
    logger.info("Found strategy class %s", cls)
    logger.info("Running strategy %s", strategy_name)

    strategy_config = config.get("strategy")
    if strategy_config is None:
        raise ValueError("There is not strategy section in config. Please provide one.")

    if mode != Mode.OPTIMIZATION:
        cls(**strategy_config).run(mode)
        return

    # Optimization mode - check for walk_forward config
    optimization_config = config.get("optimization", {})
    walk_forward_config = optimization_config.get("walk_forward")

    if walk_forward_config is not None:
        logger.info("Detected walk_forward config - running walk-forward optimization")
        run_walk_forward_optimization(cls, config)
    else:
        logger.info("Running standard optimization")
        run_optimization(cls, config)
