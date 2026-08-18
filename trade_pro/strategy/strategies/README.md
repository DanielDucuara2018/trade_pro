# Strategy Backtest Results

## ⚠️ These results supersede the previous version of this file

The previous ranking in this file was generated **before** a round of bug
fixes to the backtesting engine (`trade_pro/strategy/base.py`,
`optimization.py`, and several strategy files). Three of those bugs directly
inflated the old numbers:

1. **Position sizing ignored `position_size_pct`** whenever risk management
   was off — every trade deployed 100% of the account, turning a modest edge
   into unrealistic compounding.
2. **Look-ahead bias** in `MASStrategy`/`VolumeMASStrategy` (the daily trend
   filter leaked each day's own close into that same day's hourly candles)
   and in `VWAPStrategy` (a "yesterday's VWAP" constant computed from near
   the end of the whole dataset). Both inflated win rate and PnL.
3. **Stop-losses were never actually checked** in single-position mode for
   ATR-stop strategies (`RSIStrategy`, `MACDStrategy`, `BollingerBandsStrategy`,
   `MACrossoverStrategy`) — losses could run far past their configured risk cap.

All numbers below are from a **fresh run against the fixed code**
(2017-08 → 2025-08, real BTC/ETH/LINK/SOL history, real commission +
slippage). They are still not "safe to trade live" numbers — see caveats
below — but they no longer reflect bugs that were mechanically inflating
performance.

## Testing Environment

- **Test period**: full available history per symbol (~2017/2018 → 2025-08),
  hourly or daily candles depending on the strategy
- **Data source**: Binance historical data (`trade_pro/strategy/data/`)
- **Costs**: each config's own commission/slippage settings (typically
  0.04–0.1% commission, 0.05–0.1% slippage per side)
- **Engine**: Trade Pro backtesting engine, post-fix (see git history)

## ⚠️ Read this before trusting the ranking

- **Return % is not fully comparable across strategies.** Most of these
  configs don't set `use_risk_management`/`position_size_pct`, so they
  compound at 100% of the account on every trade — a strategy with 300
  trades will show a wildly larger `return_pct` than an equally-good
  strategy with 40 trades purely from compounding *more often*, not from a
  better per-trade edge. Treat `return_pct` as descriptive, not as the
  ranking criterion.
- **Statistical significance matters.** Several configs traded fewer than 20
  times over 7–8 years of history. A 39x profit factor on 12 trades is not
  evidence of an edge — it's a small sample that hasn't been contradicted
  yet. These are listed separately, not ranked alongside the rest.
- **This is still a backtest**, with a same-candle-close fill assumption
  for strategies that don't set `use_next_candle_open: true`, and no
  liquidity/market-impact modeling for large compounded position sizes.
  Nothing here should be read as "this will make money live."

### Ranking methodology

Strategies with **≥ 20 closed trades** are ranked by a composite score that
rewards profit factor and win-rate quality while penalizing drawdown and
discounting strategies that haven't traded enough to be confident in:

```
score = min(1, trades / 30)                      # statistical-significance discount
      × min(profit_factor, 10)                   # capped so one outlier PF doesn't dominate
      × (win_rate_weighted / 100)                 # value-weighted win rate
      ÷ (1 + max_drawdown_pct / 100)              # drawdown penalty
```

Strategies with **< 20 trades** are listed separately under "Insufficient
sample size" regardless of how good their numbers look.

## 🏆 Ranking by strategy type

Which underlying **strategy** tends to perform best across its configs
(best-qualifying-config average score; `StochasticStrategy` has no
qualifying config, so its number is unreliable — see below):

| Rank | Strategy               | Configs | Profitable | Best config                    | Best PF | Best return % |
| ---- | ---------------------- | ------- | ---------- | ------------------------------- | ------- | -------------- |
| 1    | `VolumeMASStrategy`     | 4       | 4/4        | volume_mas_strategy_btcusdt      | 2.50    | 679%            |
| 2    | `MACDSlopeStrategy`     | 6       | 6/6        | macd_slope_strategy_solusdt      | 3.95    | 17,251%         |
| 3    | `MASStrategy`           | 8       | 8/8        | mas_strategy_btcusdt_2           | 2.48    | 579%            |
| 4    | `EmaAtrReversalStrategy`| 3       | 3/3        | ema_atr_reversal_strategy_btcusdt_2 | 1.54 | 2,723%          |
| 5    | `RSIStrategy`           | 2       | 1/2        | rsi_strategy_btcusdt             | 1.21    | 15%             |
| 6    | `EMAStrategy`           | 2       | 2/2        | ema_strategy_ethusdt             | 1.40    | 2,618%          |
| 7    | `VWAPStrategy`          | 1       | 0/1        | vwap_strategy_btcusdt            | 0.98    | -1%             |
| 8    | `MultiEmaStrategy`      | 1       | 0/1        | multi_ema_strategy_btcusdt       | 0.91    | -10%            |
| 9    | `PiCycleStrategy`       | 1       | 1/1        | pi_cycle_strategy_btcusdt        | —       | 510% (1 trade — meaningless) |
| 10   | `MACDStrategy`          | 2       | 1/2        | macd_strategy_btcusdt            | 1.54    | 2% (10 trades)  |
| 11   | `BollingerBandsStrategy`| 1       | 0/1        | bollinger_bands_strategy         | 0.39    | -16%            |
| 12   | `MACrossoverStrategy`   | 1       | 0/1        | ma_crossover_strategy            | 0.69    | -2% (6 trades)  |
| —    | `StochasticStrategy`    | 3       | 3/3        | stochastic_strategy_btcusdt      | 39.5    | 8,292% (**12 trades — not enough data to trust**) |

**Reading this**: `VolumeMASStrategy` and `MACDSlopeStrategy` are the most
consistently solid strategy *types* — every config that's been tried is
profitable, several qualify for the top tier below, and none rely on a
handful of lucky trades. `MASStrategy` is close behind and has by far the
most configs tested (8/8 profitable), which is itself a decent robustness
signal. `StochasticStrategy` looks incredible on paper but every single
config for it has under 20 trades — it needs more testing (more symbols,
more history, or a looser entry condition) before it means anything.

## 📊 Full config-level ranking

### 🏆 Top tier (score ≥ 1.0)

| Config                              | Score | Trades | PF   | Win% (wtd) | Max DD% | Return % |
| ------------------------------------ | ----: | -----: | ---: | ---------: | ------: | -------: |
| macd_slope_strategy_solusdt           | 2.72  | 40     | 3.95 | 79.8%      | 16.0%   | 17,251%  |
| macd_slope_strategy_ethusdt           | 1.68  | 67     | 2.65 | 72.6%      | 14.1%   | 9,153%   |
| mas_strategy_btcusdt_2                | 1.63  | 113    | 2.48 | 71.3%      | 8.6%    | 579%     |
| volume_mas_strategy_btcusdt           | 1.56  | 109    | 2.50 | 71.4%      | 13.9%   | 679%     |
| volume_mas_strategy_solusdt           | 1.33  | 80     | 2.21 | 68.8%      | 14.1%   | 2,772%   |
| mas_strategy_btcusdt_4                | 1.28  | 128    | 2.11 | 67.9%      | 12.0%   | 775%     |
| volume_mas_strategy_ethusdt           | 1.17  | 89     | 2.07 | 67.4%      | 19.7%   | 797%     |
| macd_slope_strategy (generic config)  | 1.16  | 98     | 1.90 | 65.5%      | 7.7%    | 98%      |
| macd_slope_strategy_btcusdt           | 1.14  | 79     | 2.01 | 66.7%      | 17.4%   | 1,841%   |

### ⭐ Solid tier (0.5 ≤ score < 1.0)

| Config                              | Score | Trades | PF   | Win% (wtd) | Max DD% | Return % |
| ------------------------------------ | ----: | -----: | ---: | ---------: | ------: | -------: |
| mas_strategy_btcusdt                  | 0.86  | 213    | 1.68 | 62.8%      | 22.5%   | 1,522%   |
| mas_strategy_ethusdt                  | 0.85  | 220    | 1.59 | 61.4%      | 14.8%   | 1,183%   |
| macd_slope_strategy_linkusdt          | 0.75  | 124    | 1.59 | 61.4%      | 30.5%   | 2,410%   |
| ema_atr_reversal_strategy_btcusdt_2   | 0.75  | 133    | 1.54 | 60.6%      | 24.9%   | 2,723%   |
| ema_atr_reversal_strategy_btcusdt     | 0.72  | 46     | 1.63 | 61.9%      | 39.7%   | 2,151%   |
| mas_strategy_ethusdt_2                | 0.69  | 98     | 1.53 | 60.5%      | 33.7%   | 345%     |
| mas_strategy_btcusdt_3                | 0.67  | 167    | 1.52 | 60.4%      | 36.5%   | 718%     |
| ema_atr_reversal_strategy_btcusdt_3   | 0.66  | 131    | 1.43 | 58.8%      | 27.1%   | 2,226%   |
| rsi_strategy_btcusdt                  | 0.58  | 43     | 1.21 | 54.8%      | 15.4%   | 15%      |
| ema_strategy_ethusdt                  | 0.56  | 335    | 1.40 | 58.3%      | 45.7%   | 2,618%   |
| ema_strategy_btcusdt                  | 0.54  | 778    | 1.29 | 56.4%      | 36.2%   | 1,329%   |
| mas_strategy_btcusdt_5                | 0.51  | 359    | 1.25 | 55.6%      | 36.5%   | 491%     |

### ⚠️ Marginal (barely profitable, score < 0.5)

| Config                | Score | Trades | PF     | Win% (wtd) | Max DD% | Return % |
| ---------------------- | ----: | -----: | -----: | ---------: | ------: | -------: |
| mas_strategy_btcusdt_6 | 0.37  | 302    | 1.00   | 50.1%      | 37.6%   | 1.2%     |

### ❌ Losing (profit factor < 1)

| Config                     | Score | Trades | PF   | Win% (wtd) | Max DD% | Return % |
| --------------------------- | ----: | -----: | ---: | ---------: | ------: | -------: |
| vwap_strategy_btcusdt        | 0.42  | 60     | 0.98 | 49.4%      | 13.3%   | -1.4%    |
| multi_ema_strategy_btcusdt   | 0.38  | 647    | 0.91 | 47.7%      | 15.6%   | -10.0%   |
| bollinger_bands_strategy     | 0.08  | 27     | 0.39 | 27.9%      | 15.8%   | -15.8%   |

### 🔍 Insufficient sample size (< 20 trades — not ranked)

| Config                        | Trades | PF    | Return % | Note |
| ------------------------------ | -----: | ----: | -------: | ---- |
| pi_cycle_strategy_btcusdt       | 1      | —     | 510%     | A single trade is not a backtest |
| stochastic_strategy_btcusdt     | 12     | 39.5  | 8,292%   | Duplicate of the config below |
| stochastic_strategy_btcusdt_2   | 12     | 39.5  | 8,292%   | Duplicate of the config above |
| stochastic_strategy_ethusdt     | 12     | 1.45  | 191%     |      |
| macd_strategy_btcusdt           | 10     | 1.54  | 2.4%     |      |
| macd_strategy_ethusdt           | 7      | 0.95  | -0.4%    |      |
| rsi_strategy                    | 14     | 0.57  | -9.5%    | Also hit its own circuit breaker (max drawdown limit) |
| ma_crossover_strategy           | 6      | 0.69  | -2.4%    |      |
| volume_mas_strategy_btcusdt_2   | 17     | 3.44  | 82%      | Close to the 20-trade bar; promising but young |

## Key findings

1. **Best strategy types**: `VolumeMASStrategy` and `MACDSlopeStrategy` — every
   tested config is profitable, several land in the top tier, and none
   depend on a handful of trades to look good.
2. **Best individual config**: `macd_slope_strategy_solusdt` — highest score,
   highest profit factor (3.95) among adequately-sampled configs, and a
   respectable 40 trades over ~8 years.
3. **Most robust across variants**: `MASStrategy` — 8 different parameter
   sets tried, all 8 profitable, 6 of 8 in the top or solid tier. That kind
   of consistency across parameter perturbation is a better robustness
   signal than any single config's headline number.
4. **Needs more data before it can be trusted**: `StochasticStrategy` — the
   best-looking numbers in the whole set (PF 39.5), and also the least
   trustworthy, because every config for it has traded only 12 times.
5. **Currently losing money**: `BollingerBandsStrategy`, `MultiEmaStrategy`,
   and `VWAPStrategy` — all have a profit factor under 1 on real history and
   need rework (or different parameters) before further consideration.
6. **Return % is not a ranking signal** — `macd_slope_strategy_solusdt`'s
   17,251% and `stochastic_strategy_btcusdt`'s 8,292% both come substantially
   from 100%-of-balance compounding over many/few trades respectively, not
   from a demonstrated per-trade edge of that magnitude. Profit factor,
   win rate, and drawdown are the metrics worth comparing across configs;
   return % is a byproduct of those plus trade count and position sizing.

## Recommended next steps

- Re-run `StochasticStrategy` on more symbols/timeframes or loosen its entry
  condition — it needs a larger sample before its results mean anything.
- Consider turning on `use_risk_management` + a sane `position_size_pct` for
  the top-tier configs and re-measuring — the numbers above assume
  unconstrained 100%-of-balance compounding, which no real account can do.
- Investigate why `BollingerBandsStrategy`, `VWAPStrategy`, and
  `MultiEmaStrategy` are net losers: mean-reversion/VWAP-fade logic may
  simply not suit trending BTC/ETH history, or their parameters may need
  optimization (their `optimization.variables` ranges exist in their config
  files but haven't been run through `run_optimization` in this pass).
- `volume_mas_strategy_btcusdt_2` (17 trades, PF 3.44) is worth extending —
  it's 3 trades short of the significance bar and already looks strong.
