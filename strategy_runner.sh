#bash

# --- Top tier ---
nohup python trade_pro/main.py run --mode live --name VolumeMASStrategy --config volume_mas_strategy_btcusdt > volume_mas_strategy_btcusdt 2>&1 &
nohup python trade_pro/main.py run --mode live --name MASStrategy --config mas_strategy_btcusdt_2 > mas_strategy_btcusdt_2 2>&1 &
nohup python trade_pro/main.py run --mode live --name VolumeMASStrategy --config volume_mas_strategy_ethusdt > volume_mas_strategy_ethusdt 2>&1 &
nohup python trade_pro/main.py run --mode live --name VolumeMASStrategy --config volume_mas_strategy_solusdt > volume_mas_strategy_solusdt 2>&1 &
nohup python trade_pro/main.py run --mode live --name MACDSlopeStrategy --config macd_slope_strategy > macd_slope_strategy 2>&1 &
nohup python trade_pro/main.py run --mode live --name MACDSlopeStrategy --config macd_slope_strategy_btcusdt > macd_slope_strategy_btcusdt 2>&1 &
nohup python trade_pro/main.py run --mode live --name MASStrategy --config mas_strategy_btcusdt_4 > mas_strategy_btcusdt_4 2>&1 &

# --- Solid tier ---
nohup python trade_pro/main.py run --mode live --name MACDSlopeStrategy --config macd_slope_strategy_ethusdt > macd_slope_strategy_ethusdt 2>&1 &
nohup python trade_pro/main.py run --mode live --name MACDSlopeStrategy --config macd_slope_strategy_solusdt > macd_slope_strategy_solusdt 2>&1 &
nohup python trade_pro/main.py run --mode live --name MASStrategy --config mas_strategy_btcusdt > mas_strategy_btcusdt 2>&1 &
nohup python trade_pro/main.py run --mode live --name EmaAtrReversalStrategy --config ema_atr_reversal_strategy_btcusdt_2 > ema_atr_reversal_strategy_btcusdt_2 2>&1 &
nohup python trade_pro/main.py run --mode live --name EmaAtrReversalStrategy --config ema_atr_reversal_strategy_btcusdt > ema_atr_reversal_strategy_btcusdt 2>&1 &
nohup python trade_pro/main.py run --mode live --name EmaAtrReversalStrategy --config ema_atr_reversal_strategy_btcusdt_3 > ema_atr_reversal_strategy_btcusdt_3 2>&1 &
nohup python trade_pro/main.py run --mode live --name MASStrategy --config mas_strategy_ethusdt > mas_strategy_ethusdt 2>&1 &
nohup python trade_pro/main.py run --mode live --name MASStrategy --config mas_strategy_ethusdt_2 > mas_strategy_ethusdt_2 2>&1 &
nohup python trade_pro/main.py run --mode live --name MASStrategy --config mas_strategy_btcusdt_3 > mas_strategy_btcusdt_3 2>&1 &
nohup python trade_pro/main.py run --mode live --name MACDSlopeStrategy --config macd_slope_strategy_linkusdt > macd_slope_strategy_linkusdt 2>&1 &
nohup python trade_pro/main.py run --mode live --name RSIStrategy --config rsi_strategy_btcusdt > rsi_strategy_btcusdt 2>&1 &

# --- Explicitly requested despite low sample size (13 trades — see README) ---
nohup python trade_pro/main.py run --mode live --name StochasticStrategy --config stochastic_strategy_btcusdt > stochastic_strategy_btcusdt 2>&1 &
