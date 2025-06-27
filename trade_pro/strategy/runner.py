import logging

from trade_pro.strategy import get_module_class
from trade_pro.strategy.base import Mode
from trade_pro.strategy.optimization import run_optimization
from trade_pro.strategy.utils import load_strategy_config

logger = logging.getLogger(__name__)


def run(mode: str, strategy_name: str, file_name: str) -> None:
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

    run_optimization(cls, config)
