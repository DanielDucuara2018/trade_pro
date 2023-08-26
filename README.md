# trade_pro

Launch trading bot strategies and back testing

## Requirements

- Python +3.9
- Docker Compose

## pre-commit

```bash
pip install --user pre-commit
pre-commit install
pre-commit run --all-files
```

## Install

Create db in tina postgres

```bash
docker exec -it --user postgres report_calculation_postgres_1  psql -U postgres -c 'CREATE DATABASE trade_pro;'
```

## pytho venv

```bash
python3.9 -m venv venv
```

## generate docker containers

```bash
docker-compose up -d --build
```

## forwarding ports

Create a host name for trade-pro application:

```bash
sudo nano /etc/hosts
169.254.7.2 trade-pro
```

Forward port in host machine:

```bash
ssh -L 127.0.0.1:3202:trade-pro:3202 username@ip_address
```
