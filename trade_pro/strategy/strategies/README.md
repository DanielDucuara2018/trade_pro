# Backtest results

## MAS strategy

## Based on mas_strategy_btcusdt

```python
Total Trades: 302
Win Trades: 136
Lose Trades: 166
Max win: $111135.05
Max lose: $-40221.21
Win Rate (Count-Based): 45.03%
Win Rate (PnL-Weighted): 69.78%
Profit Factor: 2.31
Sharpe-like Ratio (return_pct/std): 0.31
Max Drawdown: $68613.19
Total PnL: $623721.13
Final Balance: $625721.13
```

## Based on mas_strategy_ethusdt

```python
Total Trades: 321
Win Trades: 141
Lose Trades: 180
Max win: $215476.80
Max lose: $-49466.85
Win Rate (Count-Based): 43.93%
Win Rate (PnL-Weighted): 69.12%
Profit Factor: 2.24
Sharpe-like Ratio (return_pct/std): 0.28
Max Drawdown: $114391.56
Total PnL: $1141824.12
Final Balance: $1143824.12
```

### Based on mas_strategy_btcusdt_2

```python
Total Trades: 129
Win Trades: 69
Lose Trades: 60
Max win: $5346.01
Max lose: $-1074.11
Win Rate (Count-Based): 53.49%
Win Rate (PnL-Weighted): 77.34%
Profit Factor: 3.41
Sharpe-like Ratio (return_pct/std): 0.40
Max Drawdown: $2541.82
Total PnL: $48862.77
Final Balance: $50862.77
```

### Based on mas_strategy_ethusdt_2

```python
Total Trades: 111
Win Trades: 57
Lose Trades: 54
Max win: $6559.54
Max lose: $-4403.20
Win Rate (Count-Based): 51.35%
Win Rate (PnL-Weighted): 68.63%
Profit Factor: 2.19
Sharpe-like Ratio (return_pct/std): 0.35
Max Drawdown: $6996.45
Total PnL: $35301.06
Final Balance: $37301.06
```

## MAS + Volume strategy

### Based on volume_mas_strategy_btcusdt

```python
Total Trades: 179
Win Trades: 84
Lose Trades: 95
Max win: $27113.69
Max lose: $-7344.17
Win Rate (Count-Based): 46.93%
Win Rate (PnL-Weighted): 76.76%
Profit Factor: 3.30
Sharpe-like Ratio (return_pct/std): 0.40
Max Drawdown: $13093.19
Total PnL: $273063.50
Final Balance: $275063.50
```

### Based on volume_mas_strategy_ethusdt

```python
Total Trades: 190
Win Trades: 76
Lose Trades: 114
Max win: $26225.97
Max lose: $-3818.32
Win Rate (Count-Based): 40.00%
Win Rate (PnL-Weighted): 68.26%
Profit Factor: 2.15
Sharpe-like Ratio (return_pct/std): 0.24
Max Drawdown: $14923.33
Total PnL: $106178.72
Final Balance: $108178.72
```

## EMA strategy

### ema_strategy_btcusdt

```python
Total Trades: 334
Win Trades: 120
Lose Trades: 214
Max win: $2043.62
Max lose: $-929.83
Win Rate (Count-Based): 35.93%
Win Rate (PnL-Weighted): 61.01%
Profit Factor: 1.57
Sharpe-like Ratio (return_pct/std): 0.17
Max Drawdown: $2506.00
Total PnL: $15477.25
Final Balance: $17477.25
```

## Stochastic strategy

### stochastic_strategy_btcusdt

```python
Total Trades: 11
Win Trades: 7
Lose Trades: 4
Max win: $67342.53
Max lose: $-1632.93
Win Rate (Count-Based): 63.64%
Win Rate (PnL-Weighted): 97.45%
Profit Factor: 38.22
Sharpe-like Ratio (return_pct/std): 0.61
Max Drawdown: $1632.93
Total PnL: $160405.42
Final Balance: $162405.42
```

# 📊 Summary Table

| Strategy                    | Trades | Win% | PnL ($)   | Profit Factor | Max DD ($) | Sharpe Ratio | Verdict                 |
| --------------------------- | ------ | ---- | --------- | ------------- | ---------- | ------------ | ----------------------- |
| stochastic_strategy_btcusdt | 11     | 63.6 | 160,405   | 38.22         | 1.6k       | 0.61         | ⭐️ High Edge, Low Freq |
| mas_strategy_btcusdt_2      | 129    | 53.5 | 48,863    | 3.41          | 2.5k       | 0.40         | ✅ Very Solid           |
| volume_mas_strategy_btcusdt | 179    | 46.9 | 273,063   | 3.30          | 13k        | 0.40         | ✅ Very Solid           |
| mas_strategy_ethusdt        | 321    | 43.9 | 1,141,824 | 2.24          | 114k       | 0.28         | ⚠️ Risky but Profitable |
| mas_strategy_btcusdt        | 302    | 45.0 | 623,721   | 2.31          | 68k        | 0.31         | ✅ Decent               |
| mas_strategy_ethusdt_2      | 111    | 51.4 | 35,301    | 2.19          | 7k         | 0.35         | ✅ Solid                |
| volume_mas_strategy_ethusdt | 190    | 40.0 | 106,178   | 2.15          | 14k        | 0.24         | ⚠️ Lower Edge           |
| ema_strategy_btcusdt        | 334    | 35.9 | 15,477    | 1.57          | 2.5k       | 0.17         | ❌ Weak                 |
