import logging
from typing import Any, Literal

import httpx

BASE_URL = "https://api.telegram.org"
TELEGRAM_TIMEOUT = 30

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    @property
    def url(self):
        return f"{BASE_URL}/bot{self.bot_token}"

    def _request(
        self,
        endpoint: str,
        *,
        body: dict | None = None,
        method: Literal["GET", "POST"] = "POST",
        transport: httpx.BaseTransport | None = None,
    ) -> dict[str, Any]:
        with httpx.Client(transport=transport, timeout=TELEGRAM_TIMEOUT) as client:
            response = client.request(method, f"{self.url}/{endpoint}", json=body)
        if response.status_code != httpx.codes.OK:
            msg = f"invalid HTTP status code - '{response.status_code}' - body: '{response.text}'"
            raise ConnectionError(msg)
        return response.json()

    def send_telegram_message(self, message: str) -> None:
        """Best-effort notification. A failure here (network blip, rate limit,
        bad/missing token) must never take down the caller — for live trading
        in particular, a notification going out is not part of the trading
        decision itself, so this only logs a warning rather than raising.
        """
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            response = self._request("sendMessage", body=payload)
        except (httpx.HTTPError, ConnectionError) as e:
            logger.warning("Failed to send Telegram message: %s", e)
            return
        logger.info("sendMessage bot response %s", response)

    def send_get_updates(self) -> None:
        response = self._request("getUpdates")
        logger.info("getUpdates bot response %s", response)
