# Strategy Backtest Results

## ⚠️ These results supersede the previous version of this file

The previous ranking in this file was generated **before** a round of bug
fixes to the backtesting engine (`trade_pro/strategy/base.py`,
`optimization.py`, and several strategy files). Three of those bugs directly
inflated the numbers before that:

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

This version is a **second, independent re-run** on top of that fixed code,
after two more changes:

- **Market data was refreshed from Binance** (`python trade_pro/main.py
  fetch`) — every symbol/timeframe now has history through 2026-08-18, not
  just through 2025-08-12 as before. Numbers below reflect roughly a year of
  additional real market data per symbol.
- **Chart files no longer collide.** `Base.generate_chart()` used to name
  its PNG output `{symbol}_{class_name}_*.png`. Several strategies —
  `MASStrategy` alone ships 8 different parameter sets — reuse the same
  class + symbol, so every config was silently overwriting the previous
  one's saved chart on disk; only the last-run config's chart ever survived.
  Charts are now named per config (`{symbol}_{config_name}_*.png`), and a
  regression test (`tests/test_strategy_configs.py`) asserts every config
  produces its own distinct, freshly-generated image.

All numbers below are from that fresh run: real BTC/ETH/LINK/SOL history
through 2026-08-18, real commission + slippage, current code. They are
still not "safe to trade live" numbers — see caveats below.

## Testing Environment

- **Test period**: full available history per symbol (~2017/2018 →
  2026-08-18), hourly or daily candles depending on the strategy
- **Data source**: Binance historical data, fetched via
  `python trade_pro/main.py fetch` (public endpoint — confirmed to need no
  API key/secret; see `check_env_vars_before_fetch` in
  `trade_pro/strategy/utils.py`)
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
  times over 7–8 years of history. A 41x profit factor on 13 trades is not
  evidence of an edge — it's a small sample that hasn't been contradicted
  yet. These are listed separately, not ranked alongside the rest.
- **This is still a backtest**, with a same-candle-close fill assumption
  for strategies that don't set `use_next_candle_open: true`, and no
  liquidity/market-impact modeling for large compounded position sizes.
  Nothing here should be read as "this will make money live."
- **Numbers moved compared to the previous run**, sometimes a lot (e.g.
  `macd_slope_strategy_solusdt`'s profit factor went from 3.95 → 1.84 with
  ~11 more trades of fresh data). That swing on its own is informative: a
  config whose headline metric is that sensitive to one extra year of
  history was riding on a thin sample, which is exactly why the
  significance gate below exists.

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
(best-qualifying-config average score; a class with no qualifying config is
marked unreliable):

| Rank | Strategy                | Configs | Profitable | Best qualifying config          | Best PF | Best return % |
| ---- | ------------------------ | ------- | ---------- | -------------------------------- | ------- | -------------- |
| 1    | `VolumeMASStrategy`      | 4       | 4/4        | volume_mas_strategy_btcusdt       | 2.16    | 631%            |
| 2    | `MACDSlopeStrategy`      | 5       | 5/5        | macd_slope_strategy (generic)     | 1.78    | 93%             |
| 3    | `MASStrategy`            | 8       | 8/8        | mas_strategy_btcusdt_2            | 2.02    | 506%            |
| 4    | `EmaAtrReversalStrategy` | 3       | 3/3        | ema_atr_reversal_strategy_btcusdt_2 | 1.48  | 2,699%          |
| 5    | `RSIStrategy`            | 2       | 1/2        | rsi_strategy_btcusdt              | 1.22    | 16%             |
| 6    | `EMAStrategy`            | 2       | 2/2        | ema_strategy_ethusdt              | 1.26    | 2,087%          |
| 7    | `VWAPStrategy`           | 1       | 0/1        | vwap_strategy_btcusdt             | 0.98    | -1%             |
| 8    | `MultiEmaStrategy`       | 1       | 0/1        | multi_ema_strategy_btcusdt        | 0.90    | -13%            |
| 9    | `BollingerBandsStrategy` | 1       | 0/1        | bollinger_bands_strategy          | 0.39    | -16%            |
| —    | `PiCycleStrategy`        | 1       | 1/1        | pi_cycle_strategy_btcusdt         | —       | 510% (1 trade — meaningless) |
| —    | `MACDStrategy`           | 2       | 2/2        | macd_strategy_btcusdt             | 1.53    | 3% (13 trades — not enough data) |
| —    | `MACrossoverStrategy`    | 1       | 0/1        | ma_crossover_strategy             | 0.69    | -2% (6 trades — not enough data) |
| —    | `StochasticStrategy`     | 3       | 3/3        | stochastic_strategy_btcusdt       | 40.8    | 8,574% (**13 trades — not enough data to trust**) |

**Reading this**: `VolumeMASStrategy` remains the most consistently solid
strategy *type* — every config that's been tried is profitable, and its
best qualifying config has the highest score of anything with an adequate
sample. `MASStrategy` is again close behind with by far the most configs
tested (8/8 profitable) — that kind of consistency across parameter
perturbation is a better robustness signal than any single config's
headline number. `MACDSlopeStrategy` moved down from last time (its
best-looking config, `_solusdt`, cooled off with fresh data — see the
caveat above) but every one of its 5 configs is still profitable.
`StochasticStrategy` again looks incredible and again has zero configs with
enough trades to trust — the extra year of data didn't change that (12 → 13
trades).

## 📊 Full config-level ranking

### 🏆 Top tier (score ≥ 1.0)

| Config                              | Score | Trades | PF   | Win% (wtd) | Max DD% | Return % |
| ------------------------------------ | ----: | -----: | ---: | ---------: | ------: | -------: |
| volume_mas_strategy_btcusdt           | 1.30  | 119    | 2.16 | 68.3%      | 13.9%   | 631%     |
| mas_strategy_btcusdt_2                | 1.20  | 124    | 2.02 | 66.9%      | 12.8%   | 506%     |
| volume_mas_strategy_ethusdt           | 1.18  | 94     | 2.09 | 67.7%      | 19.7%   | 851%     |
| volume_mas_strategy_solusdt           | 1.12  | 97     | 1.93 | 65.8%      | 13.0%   | 2,667%   |
| macd_slope_strategy (generic config)  | 1.04  | 105    | 1.78 | 64.1%      | 9.6%    | 93%      |
| macd_slope_strategy_btcusdt           | 1.03  | 85     | 1.90 | 65.5%      | 20.5%   | 1,877%   |
| mas_strategy_btcusdt_4                | 1.02  | 143    | 1.84 | 64.8%      | 17.1%   | 714%     |

### ⭐ Solid tier (0.5 ≤ score < 1.0)

| Config                              | Score | Trades | PF   | Win% (wtd) | Max DD% | Return % |
| ------------------------------------ | ----: | -----: | ---: | ---------: | ------: | -------: |
| macd_slope_strategy_ethusdt           | 0.93  | 75     | 1.82 | 64.5%      | 26.5%   | 6,943%   |
| macd_slope_strategy_solusdt           | 0.90  | 51     | 1.84 | 64.8%      | 33.3%   | 11,477%  |
| mas_strategy_btcusdt                  | 0.80  | 230    | 1.60 | 61.5%      | 22.5%   | 1,497%   |
| ema_atr_reversal_strategy_btcusdt_2   | 0.68  | 142    | 1.48 | 59.7%      | 29.7%   | 2,699%   |
| ema_atr_reversal_strategy_btcusdt     | 0.63  | 47     | 1.48 | 59.7%      | 39.7%   | 1,808%   |
| ema_atr_reversal_strategy_btcusdt_3   | 0.63  | 139    | 1.42 | 58.7%      | 32.3%   | 2,349%   |
| mas_strategy_ethusdt                  | 0.61  | 242    | 1.36 | 57.6%      | 29.5%   | 869%     |
| mas_strategy_ethusdt_2                | 0.60  | 108    | 1.39 | 58.2%      | 35.1%   | 291%     |
| mas_strategy_btcusdt_3                | 0.60  | 186    | 1.40 | 58.4%      | 36.5%   | 628%     |
| macd_slope_strategy_linkusdt          | 0.59  | 140    | 1.36 | 57.5%      | 31.3%   | 1,805%   |
| rsi_strategy_btcusdt                  | 0.57  | 48     | 1.22 | 54.9%      | 16.8%   | 16%      |

### ⚠️ Marginal (barely profitable, score < 0.5)

| Config                | Score | Trades | PF   | Win% (wtd) | Max DD% | Return % |
| ---------------------- | ----: | -----: | ---: | ---------: | ------: | -------: |
| ema_strategy_ethusdt   | 0.48  | 380    | 1.26 | 55.8%      | 45.7%   | 2,087%   |
| mas_strategy_btcusdt_5 | 0.47  | 390    | 1.19 | 54.3%      | 36.5%   | 407%     |
| ema_strategy_btcusdt   | 0.45  | 889    | 1.16 | 53.8%      | 40.4%   | 879%     |
| mas_strategy_btcusdt_6 | 0.37  | 334    | 1.03 | 50.7%      | 41.0%   | 10.3%    |

### ❌ Losing (profit factor < 1)

| Config                     | Score | Trades | PF   | Win% (wtd) | Max DD% | Return % |
| --------------------------- | ----: | -----: | ---: | ---------: | ------: | -------: |
| vwap_strategy_btcusdt        | 0.42  | 60     | 0.98 | 49.4%      | 13.3%   | -1.4%    |
| multi_ema_strategy_btcusdt   | 0.36  | 723    | 0.90 | 47.3%      | 18.0%   | -12.8%   |
| bollinger_bands_strategy     | 0.08  | 27     | 0.39 | 27.9%      | 15.8%   | -15.8%   |

### 🔍 Insufficient sample size (< 20 trades — not ranked)

| Config                        | Trades | PF    | Return % | Note |
| ------------------------------ | -----: | ----: | -------: | ---- |
| pi_cycle_strategy_btcusdt       | 1      | —     | 510%     | A single trade is not a backtest |
| stochastic_strategy_btcusdt     | 13     | 40.8  | 8,574%   | Duplicate of the config below |
| stochastic_strategy_btcusdt_2   | 13     | 40.8  | 8,574%   | Duplicate of the config above |
| macd_strategy_btcusdt           | 13     | 1.53  | 3.3%     |      |
| stochastic_strategy_ethusdt     | 13     | 1.30  | 141%     |      |
| macd_strategy_ethusdt           | 9      | 1.54  | 3.9%     |      |
| rsi_strategy                    | 14     | 0.57  | -9.5%    | Also hit its own circuit breaker (max drawdown limit) |
| ma_crossover_strategy           | 6      | 0.69  | -2.4%    |      |
| volume_mas_strategy_btcusdt_2   | 18     | 3.53  | 85%      | 2 trades short of the 20-trade bar; consistently promising across both runs |

## Key findings

1. **Best strategy type**: `VolumeMASStrategy` — every tested config is
   profitable, and it now holds the top score among adequately-sampled
   configs (`volume_mas_strategy_btcusdt`, score 1.30, PF 2.16 on 119 trades).
2. **Most robust across variants**: `MASStrategy` — 8 different parameter
   sets tried, all 8 still profitable after a year of new data, 3 in the
   top tier. Consistency across parameter perturbation is a better
   robustness signal than any single config's headline number.
3. **Biggest mover**: `macd_slope_strategy_solusdt` — was the #1 config last
   run (score 2.72, PF 3.95, 40 trades); with ~11 more trades of fresh data
   its profit factor fell to 1.84 and it dropped to the solid tier. This is
   the significance gate doing its job — a config that moves this much on
   one extra year of data was never as strong as its old headline number
   suggested.
4. **Needs more data before it can be trusted**: `StochasticStrategy` — the
   best-looking numbers in the whole set (PF 40.8), still only 13 trades
   after the data refresh. Needs more symbols/timeframes or a looser entry
   condition, not more calendar time on the same one.
5. **Currently losing money**: `BollingerBandsStrategy`, `MultiEmaStrategy`,
   and `VWAPStrategy` — all have a profit factor under 1 on real history,
   consistent with the previous run.
6. **Return % is still not a ranking signal** — see the caveats section
   above. Profit factor, win rate, and drawdown are what's worth comparing
   across configs.

## Recommended next steps

- Re-run `StochasticStrategy` on more symbols/timeframes or loosen its entry
  condition — two data refreshes in a row have left it at essentially the
  same (tiny) trade count.
- `volume_mas_strategy_btcusdt_2` (18 trades, PF 3.53) is worth extending —
  it's now only 2 trades short of the significance bar and has looked
  strong in both runs.
- Consider turning on `use_risk_management` + a sane `position_size_pct` for
  the top-tier configs and re-measuring — the numbers above assume
  unconstrained 100%-of-balance compounding, which no real account can do.
- Investigate why `BollingerBandsStrategy`, `VWAPStrategy`, and
  `MultiEmaStrategy` are net losers: mean-reversion/VWAP-fade logic may
  simply not suit trending BTC/ETH history, or their parameters may need
  optimization (their `optimization.variables` ranges exist in their config
  files but haven't been run through `run_optimization` in this pass).
- Re-run this whole ranking again after the next data refresh
  (`python trade_pro/main.py fetch`) and diff it against this version —
  which configs move a lot between runs is itself useful robustness
  information, as `macd_slope_strategy_solusdt` just demonstrated.
