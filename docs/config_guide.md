# Configuration Guide

Complete guide to all configuration parameters for Trade Pro trading strategies.

**Applies to:** All strategies (MACD Slope, MA Crossover, RSI, etc.)

## Config File Structure

```json
{
    "strategy": { ... },
    "optimization": { ... }
}
```

---

## Strategy Parameters

### Basic Settings

**`symbol`** (string, required)

- Trading pair symbol
- Example: `"BTCUSDT"`

**`initial_balance`** (number, required)

- Starting capital in dollars
- Example: `2000`

**`timeframes`** (array, required)

- Candlestick timeframes to use
- Example: `["1d"]` for daily candles
- Options: `"1m"`, `"5m"`, `"1h"`, `"4h"`, `"1d"`, etc.

### Backtest/Live Settings

**`start_backtest_index`** (number)

- Where to start backtesting in historical data
- Default: `0` (start from beginning)
- Use `>0` to skip initial candles

**`start_live_index`** (number)

- Which candle to use in live mode
- Default: `-1` (most recent complete candle)
- Use `-2` for extra safety

**`use_next_candle_open`** (boolean)

- Use next candle's open price for execution (prevents look-ahead bias)
- Default: `false`
- **Recommended: `true` for realistic backtests**

### Cost Settings

**`commission`** (number)

- Trading fee percentage per trade
- Default: `0.001` (0.1%)
- Binance: `0.001` (0.1% maker/taker)

**`slippage`** (number)

- Price slippage percentage
- Default: `0.002` (0.2%)
- Accounts for market orders and price movement

### Strategy-Specific Indicators

Each strategy has its own technical indicator parameters that can be configured in the JSON file. These parameters control the strategy's entry and exit logic.

**How to find your strategy's parameters:**

1. Check the strategy class file in `trade_pro/strategy/strategies/`
2. Look for parameters in the `__init__()` method
3. See existing config files in `trade_pro/strategy/config/` for examples

**Common indicator types:**

- **Moving Averages**: `fast_window`, `slow_window`, `ema_period`
- **MACD**: `macd_fast`, `macd_slow`, `macd_signal`
- **RSI**: `rsi_period`, `rsi_overbought`, `rsi_oversold`
- **Bollinger Bands**: `bb_period`, `bb_std`
- **Stochastic**: `stoch_k_period`, `stoch_d_period`

**Example - MACD Strategy:**

```json
{
  "strategy": {
    "symbol": "BTCUSDT",
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9
  }
}
```

**Example - Moving Average Strategy:**

```json
{
  "strategy": {
    "symbol": "BTCUSDT",
    "fast_window": 10,
    "slow_window": 50
  }
}
```

**Example - RSI Strategy:**

```json
{
  "strategy": {
    "symbol": "BTCUSDT",
    "rsi_period": 14,
    "rsi_overbought": 70,
    "rsi_oversold": 30
  }
}
```

### Position Management

**`allow_multiple_positions`** (boolean)

- Allow multiple concurrent trades
- Default: `false`
- **Recommended: `false` for beginners**

**`max_concurrent_trades`** (number)

- Maximum number of simultaneous trades
- Default: `3`
- Only used if `allow_multiple_positions: true`

**`position_size_pct`** (number)

- Percentage of capital per trade (without risk management)
- Default: `1.0` (100%)
- **Warning: Use 0.95 or enable risk management**

### Risk Management

> **Important:** Risk management has two components that work independently or together:
>
> 1. **ATR-Based Stops** (`use_atr_stops`): Dynamic stop-loss/take-profit placement based on market volatility
> 2. **Position Sizing & Circuit Breakers** (`use_risk_management`): Automatic position sizing, daily loss limits, drawdown protection
>
> **Best Practice:** Enable both for comprehensive risk control.

#### ATR-Based Stops (Stop Placement)

**`use_atr_stops`** (boolean)

- Enable ATR-based stop-loss and take-profit
- Default: `false`
- **Recommended: `true`**
- Works independently OR with `use_risk_management`

**`atr_period`** (number)

- ATR calculation period
- Default: `14`
- Standard: 14 days

**`atr_stop_multiplier`** (number)

- Stop loss distance = ATR × multiplier
- Default: `2.75`
- Range: `1.5-3.0`
- Lower = tighter stops, more stop-outs
- Higher = wider stops, less stop-outs

**`risk_reward_ratio`** (number)

- Take profit distance ratio relative to stop
- Default: `3.5`
- Range: `2.0-4.0`
- TP = Stop Distance × Risk/Reward Ratio

#### Position Sizing & Circuit Breakers

**`use_risk_management`** (boolean)

- Enable automatic position sizing and circuit breakers
- Default: `false`
- **Highly recommended: `true`**
- **Requires: `use_atr_stops: true`** (needs stop distance for position sizing)

**`risk_per_trade_pct`** (number)

- Risk percentage of capital per trade
- Default: `0.02` (2%)
- Conservative: `0.01` (1%)
- Moderate: `0.02` (2%)
- Aggressive: `0.03` (3%)
- **Requires: `use_atr_stops: true`**

**`max_daily_loss_pct`** (number)

- Maximum daily loss before circuit breaker
- Default: `0.05` (5%)
- Conservative: `0.03` (3%)
- Moderate: `0.05` (5%)
- Aggressive: `0.08` (8%)

**`max_drawdown_pct`** (number)

- Maximum drawdown from peak before circuit breaker
- Default: `0.15` (15%)
- Conservative: `0.10` (10%)
- Moderate: `0.15` (15%)
- Aggressive: `0.20` (20%)

**`min_risk_reward_ratio`** (number)

- Minimum R:R ratio required for trade entry
- Default: `2.0` (2:1)
- Conservative: `2.5`
- Moderate: `2.0`
- Aggressive: `1.5`

---

## Optimization Parameters

### Basic Optimization

**`score_method`** (string)

- Optimization scoring function
- Default: `"basic"`
- Options:
  - `"basic"` - Profit + win rate - drawdown (recommended)
  - `"risk_adjusted"` - Sharpe-like ratio
  - `"sharpe"` - Sharpe ratio
  - `"sortino"` - Sortino ratio
  - `"consistency"` - Low volatility focus
  - `"geometric_mean"` - Compound growth focus

**`n_trials`** (number)

- Number of optimization trials
- Default: `100`
- Quick test: `15-50`
- Production: `100-500`

**`n_jobs`** (number)

- Parallel workers for optimization
- Default: `1` (single core)
- Use `-1` for all CPU cores

### Parameter Ranges

**`variables`** (object)
Define optimization ranges for each parameter. Include both strategy-specific indicators AND risk management parameters:

**Example - MACD Strategy:**

```json
"variables": {
    "macd_fast": {"low": 8, "high": 16, "step": 1},
    "macd_slow": {"low": 20, "high": 32, "step": 1},
    "macd_signal": {"low": 6, "high": 12, "step": 1},
    "atr_stop_multiplier": {"low": 1.5, "high": 3.0, "step": 0.25},
    "risk_reward_ratio": {"low": 2.0, "high": 4.0, "step": 0.5}
}
```

**Example - Moving Average Strategy:**

```json
"variables": {
    "fast_window": {"low": 5, "high": 20, "step": 1},
    "slow_window": {"low": 30, "high": 100, "step": 5},
    "atr_stop_multiplier": {"low": 1.5, "high": 3.0, "step": 0.25},
    "risk_reward_ratio": {"low": 2.0, "high": 4.0, "step": 0.5}
}
```

**Note:** The exact parameters depend on your chosen strategy. Check your strategy's config file for available parameters.

### Walk-Forward Optimization

**`walk_forward`** (object)
Settings for rolling window optimization:

**`train_size`** (number)

- Training window size in days
- Default: `365` (1 year)

**`test_size`** (number)

- Test window size in days
- Default: `90` (3 months)

**`step`** (number)

- Step size for rolling window in days
- Default: `90` (quarterly)

**`min_trades`** (number)

- Minimum trades required in window
- Default: `3`
- Filters out low-activity windows

**`min_test_ratio`** (number)

- Minimum test/train score ratio to pass
- Default: `0.5` (50%)
- Validates out-of-sample performance

---

## Configuration Examples

### 1. Conservative Paper Trading

```json
{
  "strategy": {
    "symbol": "BTCUSDT",
    "initial_balance": 2000,
    "timeframes": ["1d"],
    "use_next_candle_open": true,
    "commission": 0.001,
    "slippage": 0.0005,
    "use_atr_stops": true,
    "atr_stop_multiplier": 2.5,
    "risk_reward_ratio": 3.0,
    "allow_multiple_positions": false,
    "use_risk_management": true,
    "risk_per_trade_pct": 0.01,
    "max_daily_loss_pct": 0.03,
    "max_drawdown_pct": 0.1,
    "min_risk_reward_ratio": 2.5
  }
}
```

**Note:** Add your strategy-specific indicator parameters (e.g., `macd_fast`, `rsi_period`, `fast_window`, etc.) to this config.

### 2. Moderate Backtesting

```json
{
  "strategy": {
    "symbol": "BTCUSDT",
    "initial_balance": 2000,
    "timeframes": ["1d"],
    "use_next_candle_open": true,
    "commission": 0.001,
    "slippage": 0.0005,
    "use_atr_stops": true,
    "atr_stop_multiplier": 2.75,
    "risk_reward_ratio": 3.5,
    "use_risk_management": true,
    "risk_per_trade_pct": 0.02,
    "max_daily_loss_pct": 0.05,
    "max_drawdown_pct": 0.15
  }
}
```

**Note:** Add your strategy-specific indicator parameters to this config.

### 3. Walk-Forward Optimization (MACD Strategy Example)

```json
{
  "strategy": {
    "symbol": "BTCUSDT",
    "initial_balance": 2000,
    "timeframes": ["1d"],
    "use_next_candle_open": true,
    "commission": 0.001,
    "slippage": 0.0005,
    "use_atr_stops": true
  },
  "optimization": {
    "score_method": "basic",
    "n_trials": 100,
    "variables": {
      "macd_fast": { "low": 8, "high": 16, "step": 1 },
      "macd_slow": { "low": 20, "high": 32, "step": 1 },
      "macd_signal": { "low": 6, "high": 12, "step": 1 },
      "atr_stop_multiplier": { "low": 1.5, "high": 3.0, "step": 0.25 },
      "risk_reward_ratio": { "low": 2.0, "high": 4.0, "step": 0.5 }
    },
    "walk_forward": {
      "train_size": 365,
      "test_size": 90,
      "step": 90,
      "min_trades": 3,
      "min_test_ratio": 0.5
    }
  }
}
```

### 4. Walk-Forward Optimization (Moving Average Strategy Example)

```json
{
  "strategy": {
    "symbol": "BTCUSDT",
    "initial_balance": 2000,
    "timeframes": ["1d"],
    "use_next_candle_open": true,
    "commission": 0.001,
    "slippage": 0.0005,
    "use_atr_stops": true
  },
  "optimization": {
    "score_method": "basic",
    "n_trials": 100,
    "variables": {
      "fast_window": { "low": 5, "high": 20, "step": 1 },
      "slow_window": { "low": 30, "high": 100, "step": 5 },
      "atr_stop_multiplier": { "low": 1.5, "high": 3.0, "step": 0.25 },
      "risk_reward_ratio": { "low": 2.0, "high": 4.0, "step": 0.5 }
    },
    "walk_forward": {
      "train_size": 365,
      "test_size": 90,
      "step": 90,
      "min_trades": 3,
      "min_test_ratio": 0.5
    }
  }
}
```

**Note:** Replace the indicator parameters in the `variables` section with your strategy's specific parameters.

---

## Parameter Combinations

### Risk Management + ATR Stops (Recommended)

```json
"use_atr_stops": true,
"use_risk_management": true,
"risk_per_trade_pct": 0.02
```

Position size automatically calculated from stop distance and 2% risk.

### Fixed Position Size (Simple)

```json
"use_atr_stops": true,
"use_risk_management": false,
"position_size_pct": 0.95
```

Uses 95% of capital per trade. Not recommended for live trading.

### Multiple Positions + Risk Management

```json
"allow_multiple_positions": true,
"max_concurrent_trades": 3,
"use_risk_management": true,
"risk_per_trade_pct": 0.02
```

Can have 3 trades, each risking 2% of capital.

---

## Quick Start Checklist

1. **Set Symbol**: `"symbol": "BTCUSDT"`
2. **Enable Realistic Execution**: `"use_next_candle_open": true`
3. **Enable Stops**: `"use_atr_stops": true`
4. **Enable Risk Management**: `"use_risk_management": true`
5. **Set Risk Level**: `"risk_per_trade_pct": 0.02` (2%)
6. **Set Circuit Breakers**: `"max_daily_loss_pct": 0.05` (5%)
7. **Use Optimized Parameters**: Run walk-forward optimization first

---

## Common Issues

**Issue**: "No trades executed"

- Check `start_backtest_index` - may be too high
- Check indicator parameters - may be too strict

**Issue**: "Circuit breaker triggered immediately"

- `max_daily_loss_pct` or `max_drawdown_pct` too low
- Increase limits or check strategy performance

**Issue**: "All trades skipped (R:R too low)"

- `min_risk_reward_ratio` too high
- `risk_reward_ratio` too low
- Decrease `min_risk_reward_ratio` or increase `risk_reward_ratio`

**Issue**: "Position size too small/large"

- With risk management: Adjust `risk_per_trade_pct`
- Without risk management: Adjust `position_size_pct`

---

## Tips

✅ **Always backtest before live trading**
✅ **Start with risk_per_trade_pct = 0.01 (1%) when learning**
✅ **Use walk-forward optimization to find robust parameters**
✅ **Enable circuit breakers for live trading**
✅ **Paper trade for 1-2 weeks before real money**
✅ **Monitor risk metrics daily in live trading**

❌ **Don't use position_size_pct > 0.95 without risk management**
❌ **Don't disable circuit breakers in live trading**
❌ **Don't optimize on full dataset (overfitting)**
❌ **Don't skip use_next_candle_open (look-ahead bias)**
