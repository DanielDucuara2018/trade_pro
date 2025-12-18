# Trade Pro

**Trade Pro** is a Python-based platform for algorithmic trading with professional-grade **risk management** and **modular architecture**. Built for backtesting, optimization, and live trading.

## ✨ Key Features

- **Risk Management** - Circuit breakers, risk-based position sizing, R:R validation
- **Modular Architecture** - Separated risk management, optimization, and strategy execution
- **Walk-Forward Optimization** - Find robust parameters across market conditions
- **Multiple Strategies** - MACD Slope, MA crossover, and more
- **Paper Trading** - Test with live data before risking real money
- **Professional Tools** - ATR stops, commission/slippage modeling, look-ahead bias prevention

📖 **[Complete Configuration Guide →](./docs/config_guide.md)**

## 🏗️ Architecture

```
trade_pro/strategy/
├── base.py              # Main strategy orchestrator
├── risk_manager.py      # Risk management module
├── optimization.py      # Walk-forward & standard optimization
└── strategies/          # Trading strategies
```

**Modular Benefits:**

- Clean separation of concerns
- Easy to test and maintain
- Reusable risk management
- Extensible strategy framework

## Requirements

- Python 3.12.3 or higher
- Docker and Docker Compose
- MongoDB (automatically setup with Docker)

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/DanielDucuara2018/trade_pro.git
cd trade_pro
```

### 2. Set Up Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Pre-commit Hooks (Optional but Recommended)

```bash
pip install --user pre-commit
pre-commit install
pre-commit run --all-files
```

### 4. Run Project

#### 4.1 In virtual environnement

```bash
python trade_pro/main.py run --mode backtest --name MASStrategy --config mas_strategy_btcusdt
```

#### 4.2 Trough dockerfile image

```bash
docker build -t trade_pro .
docker run --rm trade_pro run --mode backtest --name MASStrategy --config mas_strategy_btcusdt
```

#### 4.3 Trough docker compose

```bash
docker compose up -d mongo mongo-express
docker compose run --rm trade_pro run --mode backtest --name MASStrategy --config mas_strategy_btcusdt
```

## 🚀 Quick Start

### Basic Backtest (No Risk Management)

```bash
python trade_pro/main.py run --mode backtest --name MACDSlopeStrategy \
  --config macd_slope_strategy_phase6
```

### With Risk Management (Recommended)

Configure in your JSON:

```json
{
  "use_risk_management": true,
  "risk_per_trade_pct": 0.02,
  "max_daily_loss_pct": 0.05,
  "max_drawdown_pct": 0.15,
  "min_risk_reward_ratio": 2.0
}
```

**Risk Profiles:**

| Profile      | Risk/Trade | Max Daily Loss | Max Drawdown |
| ------------ | ---------- | -------------- | ------------ |
| Conservative | 1%         | 3%             | 10%          |
| Moderate     | 2%         | 5%             | 15%          |
| Aggressive   | 3%         | 8%             | 20%          |

### Walk-Forward Optimization

```bash
python trade_pro/main.py optimization --mode walk-forward \
  --name MACDSlopeStrategy --config macd_slope_strategy_phase6
```

## 📋 Essential Configuration

**Symbol & Balance:**

```json
{
  "symbol": "BTCUSDT",
  "initial_balance": 2000,
  "timeframe": "1d"
}
```

**ATR-Based Stops:**

```json
{
  "use_atr_stops": true,
  "atr_stop_multiplier": 2.5,
  "risk_reward_ratio": 3.0
}
```

**Costs (Realistic Backtests):**

```json
{
  "commission_pct": 0.001,
  "slippage_pct": 0.0005
}
```

## 📚 Documentation

- **[Configuration Guide](./docs/config_guide.md)** - Complete reference for all 30+ configuration parameters
- **[Multiple Positions](./docs/multiple_positions.md)** - Guide to managing concurrent trades with risk management
- **[Scoring Functions](./docs/scoring_functions.md)** - Detailed explanation of optimization scoring methods

### 5. Fetch market data

#### 5.1 In virtual environnement

```bash
python trade_pro/main.py fetch --ticker BTCUSDT --timeframe 1d --start-date 2017-01-01 --end-date 2025-06-13
```

#### 5.2 Trough dockerfile image

```bash
docker build -t trade_pro .
docker run --rm trade_pro fetch --ticker BTCUSDT --timeframe 1d --start-date 2017-01-01 --end-date 2025-06-13
```

#### 5.3 Trough docker compose

```bash
docker compose up -d mongo mongo-express
docker compose run --rm trade_pro fetch --ticker BTCUSDT --timeframe 1d --start-date 2017-01-01 --end-date 2025-06-13
```

## Configuration

Strategies are configured using YAML files in the `configs/` directory. Example configuration:

```yaml
strategy:
  name: "MAS"
  symbol: "BTCUSDT"
  timeframe: "1d"
  initial_balance: 1000

optimization:
  score_method: "geometric_mean" # Available: basic, risk_adjusted, sharpe, sortino, etc.
  n_trials: 1000
  variables:
    fast_window:
      low: 5
      high: 50
    slow_window:
      low: 20
      high: 200
```

## Available Strategies

- **MAS (Moving Average Strategy)**: Classic moving average crossover
- **RSI Strategy**: Relative Strength Index based trading
- Custom strategies can be implemented by extending the Base strategy class

See [Strategies Documentation](trade_pro/strategy/strategies/README.md) for detailed explanations of each strategy's implementation and parameters.

## Strategy Optimization

Trade Pro includes several scoring functions for strategy optimization:

- Basic Score: Balanced approach to profit and risk
- Risk-Adjusted Score: Focuses on risk-adjusted returns
- Geometric Mean Score: Optimizes for consistent compound growth
- Sharpe/Sortino Scores: Standard risk-adjusted metrics
- Consistency Score: Emphasizes stable returns

See [Scoring Functions Documentation](./docs/scoring_functions.md) for detailed explanations.

## Project Structure

```
trade_pro/
├── configs/            - Strategy configuration files
├── data/              - Market data storage
├── docs/              - Documentation files
├── trade_pro/
│   ├── strategy/      - Trading strategy implementations
│   │   ├── base.py    - Base strategy class
│   │   ├── mas.py     - Moving Average Strategy
│   │   ├── strategies/
│   │   │   └── README.md  - Strategies documentation
│   │   └── optimization.py - Strategy optimization
│   ├── database/      - Database interactions
│   ├── exchange/      - Exchange connectors
│   └── utils/         - Utility functions
├── tests/             - Test suite
├── Dockerfile         - Docker configuration
└── docker-compose.yml - Docker services setup
```

## Development

### Creating a New Strategy

1. Create a new file in `trade_pro/strategy/`
2. Extend the `Base` strategy class
3. Implement required methods:
   - `calculate_signals()`
   - `should_long()`
   - `should_short()`

Example:

```python
from trade_pro.strategy.base import Base

class MyStrategy(Base):
    def calculate_signals(self):
        # Your signal logic here
        pass
```

### Testing

```bash
pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

Please follow our coding standards:

- Use Black for code formatting
- Add docstrings for new functions/classes
- Update documentation for significant changes

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
