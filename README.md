# Trade Pro

**Trade Pro** is a Python-based platform designed for launching trading bot strategies and performing backtesting. It facilitates the development, testing, and deployment of algorithmic trading strategies using a Dockerized environment.

## Features

- Execute automated trading strategies
- Backtest strategies against historical data
- Dockerized setup for consistent development and deployment
- Pre-commit hooks for code quality assurance

## Requirements

- Python 3.12.3 or higher
- Docker and Docker Compose

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
python trade_pro/main.py run --mode backtest --name mas_strategy --config mas_strategy_btcusdt
```

#### 4.2 Trough dockerfile image

```bash
docker build -t trade_pro .
docker run --rm trade_pro run --mode backtest --name mas_strategy --config mas_strategy_btcusdt
```

#### 4.3 Trough docker compose

```bash
docker compose up -d mongo mongo-express
docker compose run --rm trade_pro run --mode backtest --name mas_strategy --config mas_strategy_btcusdt
```

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

## Project Structure

- `trade_pro/` - Core application code
- `Dockerfile` - Docker configuration for the application
- `docker-compose.yml` - Docker Compose setup
- `pyproject.toml` - Python project configurations

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your enhancements.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
