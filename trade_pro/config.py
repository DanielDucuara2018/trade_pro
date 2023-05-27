import logging
import os
from typing import Optional

from binance import AsyncClient

binance_api_key: Optional[str] = os.environ.get("binance_api_key")
binance_secret_key: Optional[str] = os.environ.get("binance_secret_key")
telegram_bot_token: Optional[str] = os.environ.get("telegram_bot_token")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


async def create_binance_client():
    return await AsyncClient.create(binance_api_key, binance_secret_key)
