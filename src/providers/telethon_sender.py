"""Fallback destination sender via Telethon (T053).

Credentials come only from the environment (Secrets), never from files.
"""
from __future__ import annotations

import logging

from src.models import Destination
from src.providers.base import SendResult

log = logging.getLogger("forwarder")


class TelethonSender:
    """Sends messages through a user session; classifies failures."""

    name = "telethon"

    def __init__(self, api_id=None, api_hash=None,
                 session_string=None, client=None) -> None:
        self._api_id = api_id
        self._api_hash = api_hash
        self._session = session_string
        self._client = client

    def _build_client(self):
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        if not all((self._api_id, self._api_hash, self._session)):
            raise ValueError("incomplete-credentials")
        return TelegramClient(StringSession(self._session),
                              int(self._api_id), self._api_hash)

    async def send(self, destination: Destination,
                   body: str) -> SendResult:
        client = self._client
        close = client is None
        if client is None:
            try:
                client = self._build_client()
            except ValueError:
                return SendResult(ok=False, error_class="permanent")
        try:
            await client.connect()
            if not await client.is_user_authorized():
                return SendResult(ok=False, error_class="permanent")
            msg = await client.send_message(destination.chat, body,
                                            parse_mode="html")
            return SendResult(ok=True, message_id=str(msg.id))
        except Exception as exc:  # noqa: BLE001 - map to taxonomy
            text = type(exc).__name__ + " " + str(exc)
            if ("Flood" in text or "Wait" in text or "Timeout" in text
                    or "TimedOut" in text):
                return SendResult(ok=False, error_class="retryable")
            log.warning("ارسال Telethon ناموفق بود (%s).",
                        type(exc).__name__)
            return SendResult(ok=False, error_class="permanent")
        finally:
            if close:
                try:
                    await client.disconnect()
                except Exception:  # noqa: BLE001 - best effort
                    pass
