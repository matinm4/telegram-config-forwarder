"""Public-preview scraping source provider (T022).

Adapts the fast_engine + TelegramParser approach of the reference project
(E:\\antigravity_project): no login, numeric post identity, `before`
pagination, Persian-safe text extraction.
"""
from __future__ import annotations

from typing import Optional

import httpx
from bs4 import BeautifulSoup

from src.models import Post, SourceChannel
from src.providers.base import SourceAccessError, SourceFetchError

BASE_URL = "https://t.me/s"
_MAX_PAGES = 5


def clean_username(value: str) -> str:
    cleaned = (value or "").strip().lstrip("@").rstrip("/").lower()
    if "/" in cleaned:  # tolerate full URLs
        cleaned = cleaned.rsplit("/", 1)[-1]
    return cleaned


def _parse_posts(html: str, channel: str) -> list[Post]:
    soup = BeautifulSoup(html, "html.parser")
    posts: list[Post] = []
    for el in soup.find_all("div", class_="tgme_widget_message"):
        data_post = el.get("data-post") or ""
        if "/" not in data_post:
            continue
        try:
            post_id = int(data_post.split("/", 1)[1])
        except ValueError:
            continue
        text_el = el.find("div", class_="tgme_widget_message_text")
        text = text_el.get_text(separator="\n", strip=True) if text_el else ""
        time_el = el.find("time")
        date_iso = time_el.get("datetime") if time_el else None
        views_el = el.find("span", class_="tgme_widget_message_views")
        views = views_el.get_text(strip=True) if views_el else None
        media: list[str] = []
        if el.find("a", class_="tgme_widget_message_photo_wrap"):
            media.append("photo")
        if el.find("video", class_="tgme_widget_message_video"):
            media.append("video")
        if el.find("audio"):
            media.append("audio")
        if el.find("div", class_="tgme_widget_message_document"):
            media.append("document")
        posts.append(Post(
            id=post_id, channel=channel,
            url=f"https://t.me/{channel}/{post_id}", text=text,
            date_iso=date_iso,
            is_pinned=bool(el.find(
                "div", class_="tgme_widget_message_pinned")),
            is_forwarded=bool(el.find(
                "div", class_="tgme_widget_message_forwarded_from")),
            media_types=media,
        ))
    return posts


def _before_id(html: str) -> Optional[int]:
    import re
    soup = BeautifulSoup(html, "html.parser")
    anchor = soup.find("a", class_="tme_messages_more")
    if not anchor:
        return None
    match = re.search(r"[?&]before=(\d+)", anchor.get("href", ""))
    if match:
        return int(match.group(1))
    data_before = anchor.get("data-before")
    return int(data_before) if data_before and data_before.isdigit() else None


class ScrapeSourceProvider:
    """Primary source provider: public preview, no credentials."""

    name = "scrape"

    def __init__(self, timeout: float = 20.0,
                 client: Optional[httpx.AsyncClient] = None) -> None:
        self._timeout = timeout
        self._client = client

    async def _get(self, client: httpx.AsyncClient, url: str,
                   proxy: Optional[str]) -> httpx.Response:
        # Injected test clients ignore proxy settings.
        return await client.get(url)

    async def fetch_new_posts(self, source: SourceChannel,
                              since_id: int) -> list[Post]:
        username = clean_username(source.username)
        if not username:
            raise SourceAccessError(source.id, "نام کاربری منبع نامعتبر است.")
        owned = self._client is not None
        client = self._client or httpx.AsyncClient(
            timeout=self._timeout, proxy=source.proxy,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; forwarder/1.0)"})
        try:
            found: dict[int, Post] = {}
            url = f"{BASE_URL}/{username}"
            for _ in range(_MAX_PAGES):
                try:
                    resp = await self._get(client, url, source.proxy)
                except httpx.HTTPError as exc:
                    raise SourceFetchError(
                        source.id, f"خطای شبکه در دریافت {username}."
                    ) from exc
                if resp.status_code == 404:
                    raise SourceAccessError(
                        source.id, f"کانال {username} یافت نشد.")
                if resp.status_code != 200:
                    raise SourceFetchError(
                        source.id, f"پاسخ ناموفق {resp.status_code}.")
                for post in _parse_posts(resp.text, username):
                    if post.id > since_id and not post.is_pinned:
                        found[post.id] = post
                before = _before_id(resp.text)
                if not before or min(found or {before + 1}) <= since_id:
                    break
                url = f"{BASE_URL}/{username}?before={before}"
            return [found[k] for k in sorted(found)]
        finally:
            if not owned:
                await client.aclose()
