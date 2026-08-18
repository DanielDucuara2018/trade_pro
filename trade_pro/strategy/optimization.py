import logging
from pathlib import Path
from typing import Any, Callable, Type

import numpy as np
import pandas as pd
from optuna import Trial, create_study

from trade_pro.strategy.base import Base, Mode
from trade_pro.strategy.utils import get_data

CURRENT_DIR = Path(__file__).parent
OPTI_DIR = CURRENT_DIR.joinpath("opti_results")

logger = logging.getLogger(__name__)

# TODO see if geometric average could be useful to optimize


def _get_trade_returns(strategy: Base) -> list[float]:
    """Return each closed trade's return_pct.

    strategy.trades is a dict[str, Trade] keyed by trade id — iterating it
    directly (`for t in strategy.trades`) yields the string keys, not Trade
    objects. Every scoring function below needs the actual Trade objects.
    """
    return [t.return_pct for t in strategy.trades.values() if t.return_pct is not None]


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
    profit_factor_score = np.log1p(strategy.profit_factor) * 500
    trade_penalty = max(0, (len(strategy.trades) - 100) * 5)  # Penalize >100 trades

    return (
        (strategy.balance - strategy.initial_balance)
        + profit_factor_score
        + (strategy.win_rate * 1000)
        - (drawdown_pct * 2000)
        - trade_penalty
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

    returns = _get_trade_returns(strategy)
    std_return = np.std(returns) if returns else 1e-6
    mean_return = np.mean(returns) if returns else 0
    drawdown_pct = strategy.max_drawdown / strategy.max_balance_seen

    sharpe_like = mean_return / std_return if std_return > 0 else 0

    return (
        sharpe_like * 1000
        - drawdown_pct * 100
        + (strategy.win_rate * 100 if len(strategy.trades) > 5 else 0)
    )


def score_risk_reward(strategy: Base, min_trades: int = 10) -> float:
    """
    Calculates an optimization score based on the ratio of average win percentage
    to average loss percentage, optionally weighted by win rate and trade count.

    Args:
        trades (list[dict]): List of trade dictionaries with at least a "pnl_pct" key.
                             Example: [{"pnl_pct": 3.2}, {"pnl_pct": -1.5}, ...]
        min_trades (int): Minimum number of trades required to consider the score valid.

    Returns:
        float: Risk-reward score. Returns -1.0 if not enough trades or no valid wins/losses.
    """
    # TODO improve this score
    trades = list(strategy.trades.values())
    if len(trades) < min_trades:
        return -1.0

    win_pcts = [t.return_pct for t in trades if t.return_pct is not None and t.return_pct > 0]
    loss_pcts = [-t.return_pct for t in trades if t.return_pct is not None and t.return_pct < 0]

    if not win_pcts or not loss_pcts:
        return -1.0

    avg_win = np.median(win_pcts)
    avg_loss = np.median(loss_pcts)
    win_rate = len(win_pcts) / len(trades)
    trade_penalty = min(1.0, len(trades) / min_trades)
    score = (avg_win / avg_loss) * win_rate
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

    returns = _get_trade_returns(strategy)
    multipliers = [1 + r for r in returns]
    if not multipliers or any(m <= 0 for m in multipliers):
        return -float("inf")

    geo_mean = np.prod(multipliers) ** (1 / len(multipliers)) - 1
    drawdown_pct = strategy.max_drawdown / strategy.max_balance_seen
    skewness = (np.mean(returns) - np.median(returns)) if returns else 0

    return (
        geo_mean * 1_000
        - drawdown_pct * 100
        + (len(strategy.trades) if geo_mean > 0 else 0)
        - (abs(skewness) * 100)  # Penalize negative skew
    )


def score_sharpe(strategy: Base) -> float:
    """
    Sharpe ratio-based score.
    """
    returns = _get_trade_returns(strategy)
    if len(returns) < 2 or strategy.balance <= 0:
        return -float("inf")
    mean_return = np.mean(returns)
    std_return = np.std(returns)
    if std_return == 0:
        return -float("inf")
    drawdown_pct = strategy.max_drawdown / strategy.max_balance_seen
    return (mean_return / std_return) * 1000 - drawdown_pct * 100


def score_sortino(strategy: Base) -> float:
    """
    Sortino ratio-based score.
    """
    returns = _get_trade_returns(strategy)
    if len(returns) < 2 or strategy.balance <= 0:
        return -float("inf")
    downside_returns = [r for r in returns if r < 0]
    std_downside = np.std(downside_returns) if downside_returns else 1e-6
    if std_downside == 0:
        # No variance among losing trades (e.g. every loss identical, or a
        # single losing trade) — avoid a divide-by-zero blowing up to ±inf.
        return -float("inf")
    mean_return = np.mean(returns)
    drawdown_pct = strategy.max_drawdown / strategy.max_balance_seen
    return (mean_return / std_downside) * 1000 - drawdown_pct * 100


def score_consistency(strategy: Base) -> float:
    """
    Rewards low volatility and high win rate.
    """
    returns = _get_trade_returns(strategy)
    if len(returns) < 2 or strategy.balance <= 0:
        return -float("inf")
    std_return = np.std(returns)
    win_rate = strategy.win_rate
    drawdown_pct = strategy.max_drawdown / strategy.max_balance_seen
    return win_rate * 1000 - std_return * 500 - drawdown_pct * 100


# --- Score selector mapping ---
SCORE_METHODS: dict[str, Callable[[Base], float]] = {
    "basic": score_basic,
    "balance_consistency": score_reward_balance_and_consistency,
    "risk_adjusted": score_risk_adjusted,
    "risk_reward": score_risk_reward,
    "geometric_mean": score_geometric_mean,
    "sharpe": score_sharpe,
    "sortino": score_sortino,
    "consistency": score_consistency,
}


def select_suggest_type(trial: Trial, param: str, **kwargs) -> int | float:
    if isinstance(kwargs["low"], int):
        return trial.suggest_int(param, **kwargs)
    elif isinstance(kwargs["low"], float):
        return trial.suggest_float(param, **kwargs)
    else:
        raise ValueError(f"There is not a suggest type defined for {type(kwargs['low'])}")


def _get_optimization_config(config: dict[str, Any]) -> tuple[dict, dict, str, Callable, int, int]:
    """Extract and validate optimization configuration"""
    optimization_config: dict[str, Any] = config.get("optimization")
    if optimization_config is None:
        raise ValueError("There is not optimization section in config. Please provide one.")

    optimization_variables = optimization_config.get("variables")
    if optimization_variables is None:
        raise ValueError(
            "There is no variables section in optimization config. Please provide one."
        )

    score_method_name = optimization_config.get("score_method", "basic")
    scoring_function = SCORE_METHODS.get(score_method_name)
    if scoring_function is None:
        raise ValueError(f"Unknown scoring method: '{score_method_name}'")

    n_trials = optimization_config.get("n_trials", 1000)
    n_jobs = optimization_config.get("n_jobs", -1)

    return (
        optimization_config,
        optimization_variables,
        score_method_name,
        scoring_function,
        n_trials,
        n_jobs,
    )


def _create_simple_objective(
    cls: Type[Base],
    config: dict[str, Any],
    optimization_variables: dict,
    scoring_function: Callable,
) -> Callable:
    """Create objective function for standard optimization"""

    def objective(trial: Trial) -> float:
        optimization_values = {
            param: select_suggest_type(trial, param, **kwargs)
            for param, kwargs in optimization_variables.items()
        }
        strategy_config = config["strategy"] | optimization_values
        strategy_instance = cls(**strategy_config)
        strategy_instance.run(Mode.OPTIMIZATION)
        return scoring_function(strategy_instance)

    return objective


def run_optimization(cls: Type[Base], config: dict[str, Any]) -> None:
    """Run standard optimization on full dataset"""
    OPTI_DIR.mkdir(parents=True, exist_ok=True)
    symbol = config["strategy"]["symbol"]

    _, optimization_variables, score_method_name, scoring_function, n_trials, n_jobs = (
        _get_optimization_config(config)
    )
    objective = _create_simple_objective(cls, config, optimization_variables, scoring_function)

    logger.info("Run optimization process for %s with score %s", cls.__name__, score_method_name)
    study = create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, n_jobs=n_jobs)

    print("\nBest Parameters Found:")
    print(study.best_params)
    print(f"Best score: {study.best_value:.2f}")

    study.trials_dataframe().to_csv(
        OPTI_DIR.joinpath(f"{cls.__name__}_{score_method_name}_{symbol}.csv"), index=False
    )


def _filter_trades_in_window(
    trades: dict, window_start: int, window_end: int, primary_df: pd.DataFrame
) -> dict:
    """Filter trades to those occurring within a specific time window"""
    return {
        tid: t
        for tid, t in trades.items()
        if t.is_closed and window_start <= primary_df.index.get_loc(t.entry_time) < window_end
    }


def _create_train_objective(
    cls: Type[Base],
    config: dict[str, Any],
    optimization_variables: dict,
    scoring_function: Callable,
    current_start: int,
    train_end: int,
    primary_df: pd.DataFrame,
    min_trades: int,
) -> Callable:
    """Create objective function for training window optimization"""

    def train_objective(trial: Trial) -> float:
        optimization_values = {
            param: select_suggest_type(trial, param, **kwargs)
            for param, kwargs in optimization_variables.items()
        }

        strategy_config = config["strategy"] | optimization_values
        strategy_config["start_backtest_index"] = current_start
        # Bound the backtest to the training window itself
        strategy_config["end_backtest_index"] = train_end
        strategy_instance = cls(**strategy_config)
        strategy_instance.run(Mode.OPTIMIZATION)

        # Only consider training period data
        train_trades = _filter_trades_in_window(
            strategy_instance.trades, current_start, train_end, primary_df
        )

        if len(train_trades) < min_trades:
            return -float("inf")

        # Create temporary strategy object with only train trades for scoring
        temp_strategy = cls(**strategy_config)
        temp_strategy.trades = train_trades
        temp_strategy.balance = strategy_instance.balance
        temp_strategy.max_drawdown = strategy_instance.max_drawdown
        temp_strategy.max_balance_seen = strategy_instance.max_balance_seen
        temp_strategy.win_rate = strategy_instance.win_rate
        temp_strategy.profit_factor = strategy_instance.profit_factor

        return scoring_function(temp_strategy)

    return train_objective


def _optimize_on_train_window(
    cls: Type[Base],
    config: dict[str, Any],
    optimization_variables: dict,
    scoring_function: Callable,
    current_start: int,
    train_end: int,
    primary_df: pd.DataFrame,
    min_trades: int,
    n_trials: int,
) -> tuple[dict, float]:
    """Optimize parameters on training window"""
    train_objective = _create_train_objective(
        cls,
        config,
        optimization_variables,
        scoring_function,
        current_start,
        train_end,
        primary_df,
        min_trades,
    )

    logger.info("\nOptimizing on training window ({n_trials} trials)...")
    study = create_study(direction="maximize")
    study.optimize(train_objective, n_trials=n_trials, show_progress_bar=False)

    return study.best_params, study.best_value


def _validate_on_test_window(
    cls: Type[Base],
    config: dict[str, Any],
    best_params: dict,
    scoring_function: Callable,
    test_start: int,
    test_end: int,
    primary_df: pd.DataFrame,
    min_trades: int,
    train_score: float,
) -> tuple[float, float, int]:
    """Validate best parameters on out-of-sample test window"""
    logger.info("\nTesting on out-of-sample window...")
    test_config = config["strategy"] | best_params
    test_config["start_backtest_index"] = test_start
    # Bound the backtest to the test window itself
    test_config["end_backtest_index"] = test_end
    test_strategy = cls(**test_config)
    test_strategy.run(Mode.OPTIMIZATION)

    # Filter to only test period trades
    test_trades = _filter_trades_in_window(test_strategy.trades, test_start, test_end, primary_df)

    # Calculate test score
    test_strategy.trades = test_trades
    if len(test_trades) >= min_trades:
        test_score = scoring_function(test_strategy)
        test_ratio = test_score / train_score if train_score > 0 else 0
    else:
        test_score = -float("inf")
        test_ratio = 0

    logger.info(f"Test trades: {len(test_trades)}")
    logger.info(f"Test score: {test_score:.2f}")
    logger.info(f"Test/Train ratio: {test_ratio:.2%}")

    return test_score, test_ratio, len(test_trades)


def _get_most_recent_recommendation(passed_df: pd.DataFrame) -> dict:
    """Get most recent passed window parameters"""
    return passed_df.iloc[-1].to_dict()


def _get_best_performance_recommendation(passed_df: pd.DataFrame) -> dict:
    """Get window with best out-of-sample test score"""
    return passed_df.loc[passed_df["test_score"].idxmax()].to_dict()


def _get_most_robust_recommendation(passed_df: pd.DataFrame) -> dict:
    """Get window with best test/train ratio (generalization)"""
    return passed_df.loc[passed_df["test_ratio"].idxmax()].to_dict()


def _get_median_parameters(passed_df: pd.DataFrame) -> dict:
    """Calculate median parameters across all passed windows"""
    param_names = list(passed_df.iloc[0]["best_params"].keys())
    median_params = {}
    for param in param_names:
        values = [w["best_params"][param] for _, w in passed_df.iterrows()]
        median_params[param] = round(np.median(values), 2)
    return median_params


def _print_recommendation(
    rec_num: int, title: str, window_data: dict, extra_info: str = ""
) -> None:
    """Print a single parameter recommendation"""
    logger.info(f"\n{rec_num}. {title}:")
    logger.info(
        f"   Window {window_data['window']}: {window_data['test_start']} to {window_data['test_end']}"
    )
    logger.info(f"   Parameters: {window_data['best_params']}")
    logger.info(
        f"   Test score: {window_data['test_score']:.2f}, Test ratio: {window_data['test_ratio']:.2%}"
    )
    if extra_info:
        logger.info(f"   {extra_info}")


def _print_recommendations(passed_df: pd.DataFrame) -> None:
    """Print all 4 parameter recommendations"""
    logger.info(f"\n{'=' * 70}")
    logger.info("PARAMETER RECOMMENDATIONS")
    logger.info(f"{'=' * 70}")

    # 1. Most recent
    most_recent = _get_most_recent_recommendation(passed_df)
    _print_recommendation(1, "MOST RECENT (adapts to current market)", most_recent)

    # 2. Best performance
    best_performance = _get_best_performance_recommendation(passed_df)
    _print_recommendation(2, "BEST OUT-OF-SAMPLE PERFORMANCE", best_performance)

    # 3. Most robust
    most_robust = _get_most_robust_recommendation(passed_df)
    _print_recommendation(3, "MOST ROBUST (best generalization)", most_robust)

    # 4. Median parameters
    median_params = _get_median_parameters(passed_df)
    logger.info(f"\n4. MEDIAN PARAMETERS (across {len(passed_df)} passed windows):")
    logger.info(f"   Parameters: {median_params}")
    logger.info("   Use these for a balanced approach across different market conditions")


def _print_walk_forward_summary(
    window_results: list[dict], cls: Type[Base], score_method_name: str, symbol: str
) -> None:
    """Print and save walk-forward optimization summary with parameter recommendations"""
    logger.info(f"\n{'=' * 70}")
    logger.info("WALK-FORWARD OPTIMIZATION SUMMARY")
    logger.info(f"{'=' * 70}")

    results_df = pd.DataFrame(window_results)
    passed_windows = sum(1 for w in window_results if w["passed"])
    avg_test_ratio = np.mean([w["test_ratio"] for w in window_results])

    logger.info(f"Total windows: {len(window_results)}")
    logger.info(
        f"Passed windows: {passed_windows}/{len(window_results)} ({passed_windows / len(window_results) * 100:.1f}%)"
    )
    logger.info(f"Average test/train ratio: {avg_test_ratio:.2%}")

    # Parameter recommendations
    if passed_windows > 0:
        passed_df = results_df[results_df["passed"]].copy()
        _print_recommendations(passed_df)
    else:
        logger.info("\n⚠️  No windows passed the test ratio threshold")
        logger.info("   Consider lowering min_test_ratio or adjusting parameter ranges")

    # Save detailed results
    output_file = OPTI_DIR.joinpath(f"{cls.__name__}_walk_forward_{score_method_name}_{symbol}.csv")
    results_df.to_csv(output_file, index=False)
    logger.info(f"\nDetailed results saved to: {output_file}")


def run_walk_forward_optimization(cls: Type[Base], config: dict[str, Any]) -> None:
    """
    Walk-forward optimization: optimize on train window, test on out-of-sample window.

    For each rolling window:
    1. Optimize parameters on training period
    2. Test best parameters on out-of-sample test period
    3. Compare in-sample vs out-of-sample performance
    4. Aggregate results across all windows
    """
    OPTI_DIR.mkdir(parents=True, exist_ok=True)
    symbol = config["strategy"]["symbol"]

    (
        optimization_config,
        optimization_variables,
        score_method_name,
        scoring_function,
        n_trials,
        _,
    ) = _get_optimization_config(config)

    # Walk-forward parameters
    wf_config = optimization_config.get("walk_forward", {})
    train_size = wf_config.get("train_size", 365)
    test_size = wf_config.get("test_size", 90)
    step_size = wf_config.get("step", 90)
    min_trades = wf_config.get("min_trades", 50)
    min_test_ratio = wf_config.get("min_test_ratio", 0.6)

    # Load full dataset
    timeframes = config["strategy"]["timeframes"]
    histo_data = {timeframe: get_data(symbol, timeframe) for timeframe in timeframes}
    primary_df = histo_data[timeframes[0]]
    total_length = len(primary_df)

    logger.info("\n" + "=" * 70)
    logger.info("WALK-FORWARD OPTIMIZATION")
    logger.info("=" * 70)
    logger.info(
        f"Train size: {train_size} days | Test size: {test_size} days | Step: {step_size} days"
    )
    logger.info(f"Min trades: {min_trades} | Min test ratio: {min_test_ratio}")

    window_results = []
    current_start = 0
    window_num = 1

    while current_start + train_size + test_size <= total_length:
        train_end = current_start + train_size
        test_start = train_end
        test_end = min(test_start + test_size, total_length)

        logger.info(f"\n{'=' * 70}")
        logger.info(f"Window {window_num}")
        logger.info(f"{'=' * 70}")
        logger.info(
            f"Train: {primary_df.iloc[current_start].name} to {primary_df.iloc[train_end - 1].name} ({train_size} bars)"
        )
        logger.info(
            f"Test:  {primary_df.iloc[test_start].name} to {primary_df.iloc[test_end - 1].name} ({test_size} bars)"
        )

        # Train: Optimize on training window
        best_params, train_score = _optimize_on_train_window(
            cls,
            config,
            optimization_variables,
            scoring_function,
            current_start,
            train_end,
            primary_df,
            min_trades,
            n_trials,
        )
        logger.info(f"Best parameters: {best_params}")
        logger.info(f"Train score: {train_score:.2f}")

        # Test: Validate on out-of-sample window
        test_score, test_ratio, test_trade_count = _validate_on_test_window(
            cls,
            config,
            best_params,
            scoring_function,
            test_start,
            test_end,
            primary_df,
            min_trades,
            train_score,
        )
        logger.info(f"Passed: {'✓' if test_ratio >= min_test_ratio else '✗'}")

        # Store window result
        window_results.append(
            {
                "window": window_num,
                "train_start": primary_df.iloc[current_start].name,
                "train_end": primary_df.iloc[train_end - 1].name,
                "test_start": primary_df.iloc[test_start].name,
                "test_end": primary_df.iloc[test_end - 1].name,
                "best_params": best_params,
                "train_score": train_score,
                "test_score": test_score,
                "test_ratio": test_ratio,
                "train_trades": 0,  # Not tracking this anymore for simplicity
                "test_trades": test_trade_count,
                "passed": test_ratio >= min_test_ratio,
            }
        )

        current_start += step_size
        window_num += 1

    _print_walk_forward_summary(window_results, cls, score_method_name, symbol)
