"""On-demand (聞き逃し) API client."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import aiohttp

from ._api import api_get_json
from .const import (
    EPOCH,
    ONDEMAND_CORNERS_URL,
    ONDEMAND_NEW_ARRIVALS_URL,
    ONDEMAND_SERIES_GENRES_URL,
    ONDEMAND_SERIES_SEARCH_URL,
    ONDEMAND_SERIES_URL,
)
from .models import Genre, OndemandProgram, OndemandSeries

# Regex to extract ISO 8601 start/end from aa_contents_id.
# Example: "...;2026-03-09T17:00:03+09:00_2026-03-09T18:00:03+09:00"
_AA_DATETIME_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2})"
    r"_"
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2})$"
)


# --- Fetch functions ---


async def fetch_ondemand_new_arrivals(
    session: aiohttp.ClientSession,
) -> list[OndemandSeries]:
    """Fetch the new arrivals list."""
    data = await api_get_json(session, ONDEMAND_NEW_ARRIVALS_URL)
    return parse_ondemand_new_arrivals(data)


async def fetch_ondemand_programs(
    session: aiohttp.ClientSession,
    series_site_id: str,
    corner_site_id: str,
) -> list[OndemandProgram]:
    """Fetch episodes for a specific series corner."""
    params = {"site_id": series_site_id, "corner_site_id": corner_site_id}
    data = await api_get_json(session, ONDEMAND_SERIES_URL, params=params)
    return parse_ondemand_programs(data, series_site_id, corner_site_id)


async def fetch_ondemand_search(
    session: aiohttp.ClientSession,
    keyword: str,
) -> list[OndemandSeries]:
    """Search on-demand series by keyword."""
    params = {"keyword": keyword}
    data = await api_get_json(session, ONDEMAND_SERIES_SEARCH_URL, params=params)
    return parse_ondemand_series_list(data)


async def fetch_genres(
    session: aiohttp.ClientSession,
) -> list[Genre]:
    """Fetch the list of on-demand genres."""
    data = await api_get_json(session, ONDEMAND_SERIES_GENRES_URL)
    return parse_genres(data)


async def _fetch_ondemand_series(
    session: aiohttp.ClientSession,
    params: dict[str, str],
) -> list[OndemandSeries]:
    """Fetch on-demand series with given query parameters."""
    data = await api_get_json(session, ONDEMAND_SERIES_URL, params=params)
    return parse_ondemand_series_list(data)


async def fetch_ondemand_by_genre(
    session: aiohttp.ClientSession,
    genre: str,
) -> list[OndemandSeries]:
    """Fetch on-demand series filtered by genre."""
    return await _fetch_ondemand_series(session, {"genre": genre})


async def fetch_ondemand_by_kana(
    session: aiohttp.ClientSession,
    kana: str,
) -> list[OndemandSeries]:
    """Fetch on-demand series filtered by kana initial."""
    return await _fetch_ondemand_series(session, {"kana": kana})


async def fetch_ondemand_by_date(
    session: aiohttp.ClientSession,
    onair_date: str,
) -> list[OndemandSeries]:
    """Fetch on-demand corners by broadcast date (YYYYMMDD)."""
    params = {"onair_date": onair_date}
    data = await api_get_json(session, ONDEMAND_CORNERS_URL, params=params)
    return _parse_ondemand_items(data.get("corners", []))


# --- Parse functions ---


def parse_ondemand_new_arrivals(data: dict[str, Any]) -> list[OndemandSeries]:
    """Parse the new arrivals JSON response."""
    return _parse_ondemand_items(data.get("corners", []))


def parse_ondemand_series_list(data: dict[str, Any]) -> list[OndemandSeries]:
    """Parse a series list JSON response (search, genre, kana)."""
    return _parse_ondemand_items(data.get("series", []))


def parse_genres(data: dict[str, Any]) -> list[Genre]:
    """Parse the genres JSON response."""
    return [
        Genre(genre=g["genre"], name=g["name"])
        for g in data.get("genres", [])
    ]


def parse_ondemand_programs(
    data: dict[str, Any],
    series_site_id: str = "",
    corner_site_id: str = "",
) -> list[OndemandProgram]:
    """Parse the series detail JSON response into episodes."""
    series_title = data.get("title", "")
    thumbnail_url = data.get("thumbnail_url")
    channel_id = data.get("channel_id", "")

    programs: list[OndemandProgram] = []
    for ep in data.get("episodes", []):
        start_at, end_at = _parse_aa_datetimes(ep.get("aa_contents_id", ""))
        programs.append(
            OndemandProgram(
                title=ep.get("program_title", ""),
                description=ep.get("program_sub_title", ""),
                thumbnail_url=thumbnail_url,
                series_name=series_title,
                series_site_id=series_site_id or data.get("series_site_id", ""),
                act=ep.get("act", ""),
                channel_id=channel_id,
                stream_url=ep.get("stream_url", ""),
                start_at=start_at,
                end_at=end_at,
                episode_id=str(ep.get("id", "")) or None,
                closed_at=_parse_datetime(ep.get("closed_at", "")),
            )
        )
    return programs


def _parse_ondemand_items(items: list[dict[str, Any]]) -> list[OndemandSeries]:
    """Parse a list of corner/series items into OndemandSeries."""
    result: list[OndemandSeries] = []
    for item in items:
        result.append(
            OndemandSeries(
                title=item.get("title", ""),
                description="",
                thumbnail_url=item.get("thumbnail_url"),
                series_site_id=item.get("series_site_id", ""),
                series_name=item.get("title", ""),
                radio_broadcast=item.get("radio_broadcast", ""),
                corner_site_id=item.get("corner_site_id", ""),
                corner_name=item.get("corner_name") or None,
            )
        )
    return result


def _parse_aa_datetimes(aa_contents_id: str) -> tuple[datetime, datetime]:
    """Extract (start_at, end_at) datetimes from aa_contents_id."""
    m = _AA_DATETIME_RE.search(aa_contents_id)
    if m:
        return datetime.fromisoformat(m.group(1)), datetime.fromisoformat(m.group(2))
    return EPOCH, EPOCH


def _parse_datetime(value: str) -> datetime | None:
    """Parse an ISO 8601 or date string, returning None on failure."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
