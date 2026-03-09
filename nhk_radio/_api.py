"""Shared HTTP helpers for NHK API calls."""

from __future__ import annotations

from typing import Any

import aiohttp

from .const import REQUEST_TIMEOUT
from .errors import ApiError, NetworkError


async def api_get_json(
    session: aiohttp.ClientSession,
    url: str,
    *,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """GET a JSON endpoint, raising ApiError / NetworkError on failure."""
    try:
        async with session.get(
            url,
            params=params,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
        ) as resp:
            if resp.status != 200:
                raise ApiError(resp.status, url)
            return await resp.json()  # type: ignore[no-any-return]
    except aiohttp.ClientError as exc:
        raise NetworkError(url) from exc
