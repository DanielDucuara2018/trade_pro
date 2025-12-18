# Trading Strategy Scoring Functions

This document explains how each scoring function evaluates trading strategy performance.

## Basic Score

```math
Score_{basic} = (Balance_{final} - Balance_{initial}) + 500 \cdot \ln(1 + PF) + 1000 \cdot WR - 2000 \cdot DD_{max} - TP
```

The Basic Score combines multiple aspects of trading performance:

- Rewards absolute profit through the difference between final and initial balance
- Uses a logarithmic scaling of profit factor (×500) to reward efficient trades without overemphasizing extreme values
- Heavily weights win rate (×1000) to encourage consistency
- Strongly penalizes drawdowns (×2000) to discourage risky strategies
- Includes a trade penalty that activates when strategies exceed 100 trades to discourage excessive trading

Best used for general-purpose optimization where you want a balanced approach between profitability and risk management.

## Balance and Consistency Score

```math
Score_{balance} = (Balance_{final} - Balance_{initial}) - 3 \cdot DD_{max} + \begin{cases} 200 \cdot WR & \text{if trades} > 5 \\ 0 & \text{otherwise} \end{cases}
```

This score emphasizes stable, profitable performance:

- Primary focus on absolute profit through balance difference
- Moderate drawdown penalty (×3) allows for some calculated risks
- Win rate bonus only kicks in after 5 trades to prevent overfitting on small samples
- Simpler formula makes it easier to understand strategy behavior

Ideal for developing strategies that need to maintain steady returns while accepting moderate drawdowns.

## Risk-Adjusted Score

```math
Score_{risk} = 1000 \cdot \frac{\mu_r}{\sigma_r} - 100 \cdot DD_{max} + \begin{cases} 100 \cdot WR & \text{if trades} > 5 \\ 0 & \text{otherwise} \end{cases}
```

This score focuses on the quality of returns relative to risk:

- Uses a return-to-volatility ratio similar to the Sharpe ratio (×1000)
- Moderate drawdown penalty (×100) to maintain risk awareness
- Small win rate bonus for strategies with sufficient trades
- Particularly good at identifying strategies that generate consistent returns

Best used when risk-adjusted performance is more important than absolute returns.

## Risk-Reward Score

```math
Score_{rr} = \frac{median(W)}{median(L)} \cdot WR \cdot min(1.0, \frac{n_{trades}}{n_{min}})
```

This score evaluates the efficiency of winning vs losing trades:

- Uses median values to reduce impact of outliers
- Multiplies by win rate to reward consistency
- Includes a trade count scaling factor to prevent overfitting
- Focuses on the relationship between win size and loss size

Perfect for optimizing strategies where the size relationship between wins and losses is crucial.

## Geometric Mean Score

```math
Score_{geo} = 1000 \cdot ((\prod_{i=1}^n (1 + r_i))^{\frac{1}{n}} - 1) - 100 \cdot DD_{max} + B_t - 100 \cdot |S_k|
```

This score emphasizes long-term growth potential:

- Uses geometric mean to capture true compounded performance
- Penalizes drawdowns to maintain risk management
- Rewards strategies with more trades (if profitable)
- Penalizes skewed return distributions
- Naturally punishes volatile or inconsistent returns

Ideal for developing strategies focused on steady, long-term compound growth.

## Sharpe-based Score

```math
Score_{sharpe} = 1000 \cdot \frac{\mu_r}{\sigma_r} - 100 \cdot DD_{max}
```

A classic risk-adjusted return measure:

- Rewards higher returns per unit of volatility
- Considers both upside and downside volatility equally
- Includes drawdown penalty for additional risk control
- Simple and widely understood in finance

Best for strategies where consistent risk-adjusted returns are the primary goal.

## Sortino-based Score

```math
Score_{sortino} = 1000 \cdot \frac{\mu_r}{\sigma_d} - 100 \cdot DD_{max}
```

Similar to Sharpe but focuses on downside risk:

- Only penalizes downside volatility
- More suitable for strategies with positive skew
- Includes drawdown penalty for comprehensive risk management
- Particularly useful for strategies with irregular return distributions

Use when you want to optimize returns while specifically controlling downside risk.

## Consistency Score

```math
Score_{consistency} = 1000 \cdot WR - 500 \cdot \sigma_r - 100 \cdot DD_{max}
```

Emphasizes stability and predictability:

- Heavily weights win rate to reward consistent wins
- Penalizes overall return volatility
- Moderate drawdown penalty
- Ignores absolute returns in favor of consistency

Perfect for developing very stable strategies where consistency is more important than maximum returns.

## Score Selection Guidelines

Choose your scoring function based on your strategy's primary objectives:

1. **Capital Growth Focus**: Use Basic Score or Balance and Consistency Score
2. **Risk Management Priority**: Use Risk-Adjusted or Sortino-based Score
3. **Long-term Compounding**: Use Geometric Mean Score
4. **Win/Loss Efficiency**: Use Risk-Reward Score
5. **Stability Priority**: Use Consistency Score
6. **General Purpose**: Use Sharpe-based Score

Consider combining multiple scoring functions during development to ensure your strategy performs well across different metrics.
