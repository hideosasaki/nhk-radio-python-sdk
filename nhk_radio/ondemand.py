"""On-demand (聞き逃し) API client."""

from __future__ import annotations

from typing import Any

import aiohttp

from ._api import api_get_json
from .const import ONDEMAND_NEW_ARRIVALS_URL, ONDEMAND_SERIES_URL
from .models import (
    OndemandCorner,
    OndemandEpisode,
    OndemandSeries,
    OndemandSeriesDetail,
)


async def fetch_new_arrivals(
    session: aiohttp.ClientSession,
) -> list[OndemandSeries]:
    """Fetch the new arrivals list."""
    data = await api_get_json(session, ONDEMAND_NEW_ARRIVALS_URL)
    return parse_new_arrivals(data)


async def fetch_series(
    session: aiohttp.ClientSession,
    site_id: str,
    corner_site_id: str,
) -> OndemandSeriesDetail:
    """Fetch episodes for a specific series corner."""
    params = {"site_id": site_id, "corner_site_id": corner_site_id}
    data = await api_get_json(session, ONDEMAND_SERIES_URL, params=params)
    return parse_series_detail(data)


def parse_new_arrivals(data: dict[str, Any]) -> list[OndemandSeries]:
    """Parse the new arrivals JSON response."""
    result: list[OndemandSeries] = []
    for item in data["corners"]:
        corner = OndemandCorner(
            corner_id=str(item["id"]),
            corner_site_id=item["corner_site_id"],
            title=item.get("corner_name", "") or item["title"],
            series_site_id=item["series_site_id"],
        )
        series = OndemandSeries(
            series_id=str(item["id"]),
            site_id=item["series_site_id"],
            title=item["title"],
            description="",
            radio_broadcast=item["radio_broadcast"],
            thumbnail_url=item.get("thumbnail_url"),
            corners=[corner],
        )
        result.append(series)
    return result


def parse_series_detail(data: dict[str, Any]) -> OndemandSeriesDetail:
    """Parse the series detail JSON response."""
    series_title = data["title"]
    thumbnail_url = data.get("thumbnail_url")

    episodes: list[OndemandEpisode] = []
    for ep in data["episodes"]:
        episodes.append(
            OndemandEpisode(
                episode_id=str(ep["id"]),
                title=ep["program_title"],
                description=ep.get("program_sub_title", ""),
                stream_url=ep["stream_url"],
                onair_date=ep["onair_date"],
                closed_at=ep["closed_at"],
                thumbnail_url=thumbnail_url,
                series_name=series_title,
                act=ep.get("act", ""),
            )
        )

    return OndemandSeriesDetail(
        series_title=series_title,
        corner_title=data.get("corner_name", ""),
        thumbnail_url=thumbnail_url,
        episodes=episodes,
    )
