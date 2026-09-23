"""Primary destination sender over the Telegram Bot API (T027)."""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from src.models import Destination
from src.providers.base import SendResult

log = logging.getLogger("forwarder")


class BotApiSender:
    """Sends messages via Bot API HTTPS; classifies retryable failures."""

    name = "bot_api"

    def __init__(self, token: str,
                 client: Optional[httpx.AsyncClient] = None,
                 timeout: float = 20.0) -> None:
        self._token = token
        self._client = client
        self._timeout = timeout

    def _endpoint(self) -> str:
        return f"https://api.telegram.org/bot{self._token}/sendMessage"

    async def send(self, destination: Destination,
                   body: str) -> SendResult:
        owned = self._client is not None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            resp = await client.post(self._endpoint(), json={
                "chat_id": destination.chat,
                "text": body,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            })
        except httpx.HTTPError as exc:
            log.warning("ارسال ناموفق (شبکه) به %s.", destination.id)
            return SendResult(ok=False, error_class="retryable")
        finally:
            if not owned:
                await client.aclose()
        if resp.status_code == 200:
            try:
                mid = resp.json().get("result", {}).get("message_id")
            except ValueError:
                mid = None
            return SendResult(ok=True,
                              message_id=str(mid) if mid else None)
        if resp.status_code == 429 or resp.status_code >= 500:
            return SendResult(ok=False, error_class="retryable")
        log.warning("ارسال ناموفق (دائمی) به %s: %s.",
                    destination.id, resp.status_code)
        return SendResult(ok=False, error_class="permanent")
