# Strategy Backtest Results

## Testing Environment

- **Test Period**: 2017-01-01 to 2025-06-13
- **Initial Capital**: $2,000
- **Trading Fees**: 0.1% per trade
- **Data Source**: Binance historical data
- **Test Environment**: Trade Pro Backtesting Engine

## Performance Categories

🏆 **Elite Performers** (Profit Factor > 3.0, Sharpe > 0.4)

- Stochastic BTC Strategy
- MACD Slope SOL Strategy
- MAS BTC Strategy v2

⭐ **Strong Performers** (Profit Factor > 2.0, Sharpe > 0.3)

- Volume MAS BTC Strategy
- MAS BTC Strategy v4
- MACD Slope ETH Strategy

⚠️ **High Risk/Reward** (High PnL but high drawdown)

- Volume MAS ETH Strategy
- MAS ETH Strategy
- Volume MAS SOL Strategy

❌ **Needs Improvement** (Profit Factor < 1.5 or Sharpe < 0.2)

- EMA BTC Strategy
- MAS BTC Strategy v5

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
Max Balance Seen: $626139.13
Total PnL: $623721.13
Final Balance: $625721.13
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
Max Balance Seen: $51848.29
Total PnL: $48862.77
Final Balance: $50862.77
```

### Based on mas_strategy_btcusdt_3

```python
Total Trades: 227
Win Trades: 92
Lose Trades: 135
Max win: $87220.80
Max lose: $-12696.72
Win Rate (Count-Based): 40.53%
Win Rate (PnL-Weighted): 69.33%
Profit Factor: 2.26
Sharpe-like Ratio (return_pct/std): 0.28
Max Drawdown: $54905.65
Max Balance Seen: $324667.73
Total PnL: $301130.32
Final Balance: $303130.32
```

### Based on mas_strategy_btcusdt_4

```python
Total Trades: 140
Win Trades: 72
Lose Trades: 68
Max win: $8051.13
Max lose: $-1903.48
Win Rate (Count-Based): 51.43%
Win Rate (PnL-Weighted): 73.44%
Profit Factor: 2.76
Sharpe-like Ratio (return_pct/std): 0.36
Max Drawdown: $4852.56
Max Balance Seen: $48201.59
Total PnL: $45502.75
Final Balance: $47502.75
```

### Based on mas_strategy_btcusdt_5

```python
Total Trades: 431
Win Trades: 172
Lose Trades: 259
Max win: $40590.03
Max lose: $-11585.96
Win Rate (Count-Based): 39.91%
Win Rate (PnL-Weighted): 62.30%
Profit Factor: 1.65
Sharpe-like Ratio (return_pct/std): 0.23
Max Drawdown: $32192.76
Max Balance Seen: $209536.86
Total PnL: $204656.73
Final Balance: $206656.73
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
Max Balance Seen: $1144686.10
Total PnL: $1141824.12
Final Balance: $1143824.12
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
Max Balance Seen: $44156.27
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
Max Balance Seen: $276664.94
Total PnL: $273063.50
Final Balance: $275063.50
```

### Based on volume_mas_strategy_ethusdt

```python
Total Trades: 178
Win Trades: 72
Lose Trades: 106
Max win: $391490.33
Max lose: $-54215.69
Win Rate (Count-Based): 40.45%
Win Rate (PnL-Weighted): 73.96%
Profit Factor: 2.84
Sharpe-like Ratio (return_pct/std): 0.34
Max Drawdown: $165586.11
Max Balance Seen: $1493757.28
Total PnL: $1345196.73
Final Balance: $1347196.73
```

### volume_mas_strategy_solusdt

```python
Total Trades: 122
Win Trades: 57
Lose Trades: 65
Max win: $130311.08
Max lose: $-71553.46
Win Rate (Count-Based): 46.72%
Win Rate (PnL-Weighted): 72.78%
Profit Factor: 2.67
Sharpe-like Ratio (return_pct/std): 0.34
Max Drawdown: $106508.87
Max Balance Seen: $973196.43
Total PnL: $971196.43
Final Balance: $973196.43
```

## EMA strategy

### ema_strategy_btcusdt

```python
Total Trades: 768
Win Trades: 265
Lose Trades: 503
Max win: $3600.75
Max lose: $-1099.82
Win Rate (Count-Based): 34.51%
Win Rate (PnL-Weighted): 56.26%
Profit Factor: 1.29
Sharpe-like Ratio (return_pct/std): 0.13
Max Drawdown: $11764.63
Max Balance Seen: $32502.18
Total PnL: $25642.46
Final Balance: $27642.46
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
Max Balance Seen: $167838.06
Total PnL: $160405.42
Final Balance: $162405.42
```

## MACD Slope strategy

### macd_slope_strategy_btcusdt

```python
Total Trades: 73
Win Trades: 32
Lose Trades: 41
Max win: $8134.54
Max lose: $-2415.46
Win Rate (Count-Based): 43.84%
Win Rate (PnL-Weighted): 72.03%
Profit Factor: 2.58
Sharpe-like Ratio (return_pct/std): 0.29
Max Drawdown: $3886.61
Max Balance Seen: $46980.63
Total PnL: $44189.99
Final Balance: $46189.99
```

### macd_slope_strategy_ethusdt

```python
Total Trades: 66
Win Trades: 31
Lose Trades: 35
Max win: $44733.24
Max lose: $-11828.57
Win Rate (Count-Based): 46.97%
Win Rate (PnL-Weighted): 67.87%
Profit Factor: 2.11
Sharpe-like Ratio (return_pct/std): 0.38
Max Drawdown: $26162.64
Max Balance Seen: $125603.43
Total PnL: $123603.43
Final Balance: $125603.43
```

### macd_slope_strategy_solusdt

```python
Total Trades: 40
Win Trades: 20
Lose Trades: 20
Max win: $107728.82
Max lose: $-19073.16
Win Rate (Count-Based): 50.00%
Win Rate (PnL-Weighted): 79.79%
Profit Factor: 3.95
Sharpe-like Ratio (return_pct/std): 0.47
Max Drawdown: $55560.58
Max Balance Seen: $347025.31
Total PnL: $345025.31
Final Balance: $347025.31
```

### macd_slope_strategy_linkusdt

```python
Total Trades: 123
Win Trades: 57
Lose Trades: 66
Max win: $8938.56
Max lose: $-8839.36
Win Rate (Count-Based): 46.34%
Win Rate (PnL-Weighted): 60.29%
Profit Factor: 1.52
Sharpe-like Ratio (return_pct/std): 0.24
Max Drawdown: $16944.49
Max Balance Seen: $55474.59
Total PnL: $42111.23
Final Balance: $44111.23
```

# 📊 Performance Summary

| Strategy                    | Trades | Win%   | PnL ($)      | PF¹   | Max DD² (%) | Sharpe | Verdict              |
| --------------------------- | ------ | ------ | ------------ | ----- | ----------- | ------ | -------------------- |
| **Stochastic BTC Strategy** | 11     | 63.64% | 160,405.42   | 38.22 | 0.98        | 0.61   | 🏆 Elite Performer   |
| **MACD Slope SOL Strategy** | 40     | 50.00% | 345,025.31   | 3.95  | 55.6        | 0.47   | 🏆 Elite Performer   |
| **MAS BTC Strategy v2**     | 129    | 53.49% | 48,862.77    | 3.41  | 2.5         | 0.40   | 🏆 Elite Performer   |
| **Volume MAS BTC Strategy** | 179    | 46.93% | 273,063.50   | 3.30  | 13.0        | 0.40   | ⭐ Strong Performer  |
| **MAS BTC Strategy v4**     | 140    | 51.43% | 45,502.75    | 2.76  | 4.9         | 0.36   | ⭐ Strong Performer  |
| **MACD Slope ETH Strategy** | 66     | 46.97% | 123,603.43   | 2.11  | 26.2        | 0.38   | ⭐ Strong Performer  |
| **Volume MAS ETH Strategy** | 178    | 40.45% | 1,345,197.00 | 2.84  | 165.6       | 0.34   | ⚠️ High Risk/Reward  |
| **MAS ETH Strategy**        | 321    | 43.93% | 1,141,824.12 | 2.24  | 114.0       | 0.28   | ⚠️ High Risk/Reward  |
| **Volume MAS SOL Strategy** | 122    | 46.72% | 971,196.43   | 2.67  | 106.5       | 0.34   | ⚠️ High Risk/Reward  |
| **MAS BTC Strategy**        | 302    | 45.03% | 623,721.13   | 2.31  | 68.0        | 0.31   | ⚠️ High Risk/Reward  |
| **MAS BTC Strategy v3**     | 227    | 40.53% | 301,130.32   | 2.26  | 55.0        | 0.28   | ⚠️ High Risk/Reward  |
| **EMA BTC Strategy**        | 768    | 34.51% | 25,642.46    | 1.29  | 11.8        | 0.13   | ❌ Needs Improvement |
| **MAS BTC Strategy v5**     | 431    | 39.91% | 204,656.73   | 1.65  | 32.0        | 0.23   | ❌ Needs Improvement |

## Key Findings

1. **Best Overall Strategy**: Stochastic BTC with highest risk-adjusted returns (Sharpe 0.61)
2. **Most Consistent**: MAS BTC v2 with solid metrics across all categories
3. **Most Scalable**: Volume MAS BTC showing good balance of returns and risk
4. **Needs Optimization**: EMA BTC showing poor risk-adjusted returns
