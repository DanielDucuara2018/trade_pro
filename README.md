# Trade Pro

**Trade Pro** is a Python-based platform designed for launching trading bot strategies and performing backtesting. It facilitates the development, testing, and deployment of algorithmic trading strategies using a Dockerized environment.

## Features

* Execute automated trading strategies
* Backtest strategies against historical data
* Dockerized setup for consistent development and deployment
* Pre-commit hooks for code quality assurance

## Requirements

* Python 3.9 or higher
* Docker and Docker Compose

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/DanielDucuara2018/trade_pro.git
cd trade_pro
```

### 2. Set Up Python Virtual Environment

```bash
python3.9 -m venv venv
source venv/bin/activate
```

### 3. Install Pre-commit Hooks (Optional but Recommended)

```bash
pip install --user pre-commit
pre-commit install
pre-commit run --all-files
```

### 4. Create PostgreSQL Database

Ensure Docker is running, then execute:

```bash
docker exec -it --user postgres report_calculation_postgres_1 psql -U postgres -c 'CREATE DATABASE trade_pro;'
```

### 5. Build and Run Docker Containers

```bash
docker-compose up -d --build
```

### 6. Configure Hostname and Port Forwarding (Optional)

Add the following entry to your `/etc/hosts` file:

```bash
169.254.7.2 trade-pro
```

Set up SSH port forwarding:

```bash
ssh -L 127.0.0.1:3202:trade-pro:3202 username@ip_address
```

## Project Structure

* `trade_pro/` - Core application code
* `alembic/` - Database migration scripts
* `pgsql/init.d/` - PostgreSQL initialization scripts
* `Dockerfile` - Docker configuration for the application
* `docker-compose.yml` - Docker Compose setup
* `supervisord.conf` - Supervisor configuration
* `pyproject.toml` & `setup.py` - Python project configurations

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your enhancements.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
