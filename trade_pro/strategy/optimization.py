import logging
from pathlib import Path
from typing import Any, Callable, Type

import numpy as np
from optuna import Trial, create_study

from trade_pro.strategy.base import Base, Mode

CURRENT_DIR = Path(__file__).parent
OPTI_DIR = CURRENT_DIR.joinpath("opti_results")

logger = logging.getLogger(__name__)

# TODO see if geometric average could be useful to optimize


# --- Scoring Methods ---
def score_basic(strategy: Base) -> float:
    """
    Basic performance scoring function for trading strategies.

    This score combines absolute profit, profitability quality, and risk.

    ### Components:
    - **Net Profit**: Reward for growing the account balance.
    - **Profit Factor Bonus**: Rewards the ratio of gross profits to gross losses (scaled by 500).
    - **Win Rate Bonus**: Rewards consistency by scaling win rate (0–1) by 1000.
    - **Drawdown Penalty**: Penalizes maximum drawdown heavily (multiplied by 2000),
      since capital preservation is critical.

    ### Purpose:
    - To favor strategies with **high profit, good risk/reward ratio, and consistency**,
      while discouraging large drawdowns.

    Returns:
        float: Composite score (higher is better).
    """
    if len(strategy.trades) < 2 or strategy.balance <= 0:
        return -float("inf")

    drawdown_pct = strategy.max_drawdown / strategy.max_balance_seen
    return (
        (strategy.balance - strategy.initial_balance)
        + (strategy.profit_factor * 500)
        + (strategy.win_rate * 1000)
        - (drawdown_pct * 2000)
    )


def score_reward_balance_and_consistency(strategy: Base) -> float:
    """
    Score that emphasizes profitability and consistency with a modest drawdown penalty.

    ### Components:
    - **Net Profit**: The primary factor; rewards absolute profit.
    - **Drawdown Penalty**: Mildly penalizes maximum drawdown (×3).
    - **Win Rate Bonus**: Adds a reward for high win rate — but only if there are enough trades
      (more than 5), to avoid overfitting on small sample sizes.

    ### Purpose:
    - This score encourages strategies that are **stable and profitable over a reasonable number
      of trades**, even if drawdown is moderate.

    - Suitable for **mid-risk, mid-frequency strategies** with decent historical consistency.

    Returns:
        float: Composite score (higher is better).
    """
    if len(strategy.trades) < 2 or strategy.balance <= 0:
        return -float("inf")

    drawdown_pct = strategy.max_drawdown / strategy.max_balance_seen
    return (
        (strategy.balance - strategy.initial_balance)
        - (drawdown_pct * 3)
        + (strategy.win_rate * 200 if len(strategy.trades) > 5 else 0)
    )


def score_risk_adjusted(strategy: Base) -> float:
    """
    Risk-adjusted scoring function combining return, drawdown, and profit factor.

    ### Logic:
    - Computes a **return-to-risk ratio** using:
        - Net profit as the numerator.
        - Risk adjusted by:
            - Maximum drawdown.
            - Inverse profit factor (1 / PF), where lower values indicate better efficiency.

    - **Win Rate Bonus**:
        - Adds a scaled bonus for win rate if the number of trades exceeds 5,
          to prevent overfitting to a small sample.

    ### Purpose:
    - Encourages **efficient strategies** that achieve higher returns per unit of risk,
      rather than just high absolute profit.

    - Suitable for **comparing strategies with very different risk profiles**.

    Returns:
        float: Risk-adjusted score (higher is better).
    """
    if len(strategy.trades) < 2 or strategy.balance <= 0:
        return -float("inf")

    drawdown_pct = strategy.max_drawdown / strategy.max_balance_seen
    return (strategy.balance - strategy.initial_balance) / (
        1 + drawdown_pct + 1 / (1 + strategy.profit_factor)
    ) + (strategy.win_rate * 100 if len(strategy.trades) > 5 else 0)


def score_risk_reward(strategy: Base, min_trades: int = 10) -> float:
    """
    Calculates an optimization score based on the ratio of average win percentage
    to average loss percentage, optionally weighted by win rate and trade count.

    Args:
        trades (list[dict]): List of trade dictionaries with at least a 'pnl_pct' key.
                             Example: [{"pnl_pct": 3.2}, {"pnl_pct": -1.5}, ...]
        min_trades (int): Minimum number of trades required to consider the score valid.

    Returns:
        float: Risk-reward score. Returns -1.0 if not enough trades or no valid wins/losses.
    """
    # TODO improve this score
    trades = strategy.trades
    if len(trades) < min_trades:
        return -1.0  # Penalize unrepresentative samples

    win_pcts = [t["return_pct"] for t in trades if t["return_pct"] > 0]
    loss_pcts = [
        -t["return_pct"] for t in trades if t["return_pct"] < 0
    ]  # Convert to positive for averaging

    if not win_pcts or not loss_pcts:
        return -1.0  # No valid win or loss data

    avg_win = sum(win_pcts) / len(win_pcts)
    avg_loss = sum(loss_pcts) / len(loss_pcts)
    win_rate = len(win_pcts) / len(trades)

    # Core score: reward-to-risk ratio * win rate
    score = (avg_win / avg_loss) * win_rate

    # Optional: penalize low trade counts (< min_trades)
    trade_penalty = min(1.0, len(trades) / min_trades)
    return score * trade_penalty


def score_geometric_mean(strategy: Base) -> float:
    """
    Compute a strategy performance score using geometric mean return.

    This scoring function is designed to favor strategies that achieve
    consistent and compounding profitability over time, while penalizing
    high drawdowns and rewarding a healthy number of trades if the strategy
    is profitable overall.

    ### How it works:
    1. **Geometric Mean Return**:
        - Calculates the geometric mean of per-trade returns (in decimal form).
        - Reflects the compound rate of growth per trade, unlike the arithmetic mean.
        - Penalizes volatile or inconsistent returns, as a few large losses reduce the mean significantly.

    2. **Drawdown Penalty**:
        - Subtracts a multiple of the maximum drawdown to avoid overly risky strategies.

    3. **Trade Count Bonus**:
        - Adds a small reward for the number of trades — but only if the geometric mean is positive —
          to favor stable strategies with a sufficient number of data points.

    ### Why use geometric mean?
    - It captures **true compounded performance**.
    - It naturally discourages erratic or overfitted strategies.
    - It ensures the scoring metric aligns with long-term growth potential.

    Args:
        strategy (Base): The strategy object with executed trades and performance metrics.

    Returns:
        float: The computed score. Higher is better.
    """
    if len(strategy.trades) < 2 or strategy.balance <= 0:
        return -float("inf")

    multipliers = [1 + t["return_pct"] for t in strategy.trades if "return_pct" in t]
    if any(m <= 0 for m in multipliers):
        return -float("inf")  # Avoid math domain error or non-compounding losses

    geo_mean = np.prod(multipliers) ** (1 / len(multipliers)) - 1
    drawdown_pct = strategy.max_drawdown / strategy.max_balance_seen

    return (
        geo_mean * 1_000  # Reward geometric compounding
        - drawdown_pct * 100  # Heavily penalize large drawdowns
        + (len(strategy.trades) if geo_mean > 0 else 0)  # Reward consistency only if profitable
    )


# --- Score selector mapping ---
SCORE_METHODS: dict[str, Callable[[Base], float]] = {
    "basic": score_basic,
    "balance_consistency": score_reward_balance_and_consistency,
    "risk_adjusted": score_risk_adjusted,
    "risk_reward": score_risk_reward,
    "geometric_mean": score_geometric_mean,
}


def select_suggest_type(trial: Trial, param: str, **kwargs) -> int | float:
    if isinstance(kwargs["low"], int):
        return trial.suggest_int(param, **kwargs)
    elif isinstance(kwargs["low"], float):
        return trial.suggest_float(param, **kwargs)
    else:
        raise ValueError(f"There is not a suggest type defined for {type(kwargs['low'])}")


def run_optimization(cls: Type[Base], config: dict[str, Any]) -> None:
    OPTI_DIR.mkdir(parents=True, exist_ok=True)

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
