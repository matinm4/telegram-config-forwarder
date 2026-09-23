"""Offline GeoIP location with configurable fallback (T040)."""
from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlsplit

from src.models import ExtractedConfig, Location

log = logging.getLogger("forwarder")


def host_of(raw: str) -> Optional[str]:
    try:
        host = urlsplit(raw).hostname
    except ValueError:
        return None
    return host


class GeoIpLocator:
    """Resolves country via an injected reader; never stops the pipeline."""

    def __init__(self, reader=None, fallback_display: str = "Unknown",
                 db_path: Optional[str] = None) -> None:
        self._reader = reader
        self._fallback = fallback_display
        if reader is None and db_path:
            try:
                import geoip2.database
                self._reader = geoip2.database.Reader(db_path)
            except Exception:  # noqa: BLE001 - optional dependency path
                log.warning("پایگاه GeoIP در دسترس نیست؛ حالت جایگزین.")
                self._reader = None

    def locate(self, config: ExtractedConfig) -> Location:
        host = host_of(config.raw)
        if host and self._reader is not None:
            try:
                code = self._reader.country(host).country.iso_code
                if code:
                    return Location(country_code=code, source="geoip",
                                    display=code)
            except Exception:  # noqa: BLE001 - any lookup failure
                pass
        return Location(source="fallback", display=self._fallback)
