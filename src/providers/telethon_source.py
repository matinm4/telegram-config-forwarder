"""Secondary source provider via Telethon (T047).

Uses a pre-provisioned session string - never interactive login.
Credentials come only from the environment (Secrets).
"""
from __future__ import annotations

import logging
from typing import Optional

from src.models import Post, SourceChannel
from src.providers.base import SourceAccessError, SourceFetchError

log = logging.getLogger("forwarder")


class TelethonSourceProvider:
    """Fetch posts through the Telegram client API (private channels)."""

    name = "telethon"

    def __init__(self, api_id=None, api_hash=None,
                 session_string=None, limit: int = 50,
                 client=None) -> None:
        self._api_id = api_id
        self._api_hash = api_hash
        self._session = session_string
        self._limit = limit
        self._client = client

    def _build_client(self):
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        if not all((self._api_id, self._api_hash, self._session)):
            raise SourceAccessError(
                "-", "اعتبار Telethon کامل نیست.")
        return TelegramClient(StringSession(self._session),
                              int(self._api_id), self._api_hash)

    async def fetch_new_posts(self, source: SourceChannel,
                              since_id: int) -> list[Post]:
        username = (source.username or "").strip().lstrip("@")
        if not username:
            raise SourceAccessError(source.id, "نام کاربری منبع نامعتبر است.")
        client = self._client or self._build_client()
        close = self._client is None
        try:
            from telethon.errors import FloodWaitError
            from telethon.tl.functions.messages import GetHistoryRequest
            await client.connect()
            if not await client.is_user_authorized():
                raise SourceAccessError(
                    source.id, "نشست Telethon معتبر نیست.")
            entity = await client.get_entity(username)
            history = await client(GetHistoryRequest(
                peer=entity, limit=self._limit, offset_date=None,
                offset_id=0, max_id=0, min_id=since_id,
                add_offset=0, hash=0))
            posts = []
            for msg in sorted(history.messages, key=lambda m: m.id):
                if msg.id <= since_id:
                    continue
                posts.append(Post(
                    id=msg.id, channel=username,
                    url=f"https://t.me/{username}/{msg.id}",
                    text=getattr(msg, "message", "") or "",
                    date_iso=(msg.date.isoformat()
                              if getattr(msg, "date", None) else None)))
            return posts
        except SourceAccessError:
            raise
        except Exception as exc:  # noqa: BLE001 - map to taxonomy
            text = type(exc).__name__ + " " + str(exc)
            if "Flood" in text or "Wait" in text:
                raise SourceFetchError(
                    source.id, "محدودیت نرخ Telethon.") from exc
            if "Username" in text:
                raise SourceAccessError(
                    source.id, f"کانال {username} در دسترس نیست.") from exc
            raise SourceFetchError(
                source.id, "خطای Telethon در دریافت.") from exc
        finally:
            if close:
                try:
                    await client.disconnect()
                except Exception:  # noqa: BLE001 - best effort
                    pass
