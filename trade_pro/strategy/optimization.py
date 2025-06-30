import logging
from pathlib import Path
from typing import Any, Callable, Type

from optuna import Trial, create_study

from trade_pro.strategy.base import Base, Mode

CURRENT_DIR = Path(__file__).parent
OPTI_DIR = CURRENT_DIR.joinpath("opti_results")

logger = logging.getLogger(__name__)


# --- Scoring Methods ---
def score_basic(strategy: Base) -> float:
    return (
        (strategy.balance - strategy.initial_balance)
        + (strategy.profit_factor * 500)
        + (strategy.win_rate * 1000)
        - (strategy.max_drawdown * 2000)
    )


def score_reward_balance_and_consistency(strategy: Base) -> float:
    return (
        (strategy.balance - strategy.initial_balance)
        - (strategy.max_drawdown * 3)
        + (strategy.win_rate * 200 if len(strategy.trades) > 5 else 0)
    )


def score_risk_adjusted(strategy: Base) -> float:
    return (strategy.balance - strategy.initial_balance) / (
        1 + strategy.max_drawdown + 1 / (1 + strategy.profit_factor)
    ) + (strategy.win_rate * 100 if len(strategy.trades) > 5 else 0)


# --- Score selector mapping ---
SCORE_METHODS: dict[str, Callable[[Base], float]] = {
    "basic": score_basic,
    "balance_consistency": score_reward_balance_and_consistency,
    "risk_adjusted": score_risk_adjusted,
}


def select_suggest_type(trial: Trial, param: str, **kwargs) -> int | float:
    if isinstance(kwargs["low"], int):
        return trial.suggest_int(param, **kwargs)
    elif isinstance(kwargs["low"], float):
        return trial.suggest_float(param, **kwargs)
    else:
        raise ValueError(f"There is not a suggest type defined for {type(kwargs['low'])}")


def run_optimization(cls: Type[Base], config: dict[str, Any]) -> None:
    symbol = config["strategy"]["symbol"]
    optimization_config: dict[str, Any] = config.get("optimization")

    if optimization_config is None:
        raise ValueError("There is not optimization section in config. Please provide one.")

    optimization_variables = optimization_config.get("variables")
    if optimization_config is None:
        raise ValueError("There is not optimization section in config. Please provide one.")

    score_method_name = optimization_config.get("score_method", "sharpe_like")  # Default fallback
    scoring_function = SCORE_METHODS.get(score_method_name)

    if scoring_function is None:
        raise ValueError(f"Unknown scoring method: '{score_method_name}'")

    n_trials = optimization_config.get("n_trials", 1000)
    n_jobs = optimization_config.get("n_trials", -1)

    def objective(trial: Trial) -> float:
        optimization_values = {
            param: select_suggest_type(trial, param, **kwargs)
            for param, kwargs in optimization_variables.items()
        }

        strategy_config = config["strategy"] | optimization_values
        strategy_instance = cls(**strategy_config)
        strategy_instance.run(Mode.OPTIMIZATION)

        return scoring_function(strategy_instance)

    logger.info("Run optimization process for %s with score %s", cls.__name__, score_method_name)
    study = create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, n_jobs=n_jobs)

    print("\nBest Parameters Found:")
    print(study.best_params)
    print(f"Best score: {study.best_value:.2f}")

    study.trials_dataframe().to_csv(
        OPTI_DIR.joinpath(f"{cls.__name__}_{score_method_name}_{symbol}.csv"), index=False
    )
