FROM python:3.12.3-slim

WORKDIR /app
COPY pyproject.toml .
COPY trade_pro trade_pro

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    build-essential &&\
    rm -rf /var/lib/apt/lists/*
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -e .

ENTRYPOINT ["python", "trade_pro/main.py"]
