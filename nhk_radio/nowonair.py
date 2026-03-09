"""Now-on-air (NOA) program information API client."""

from __future__ import annotations

from typing import Any

import aiohttp

from ._api import api_get_json
from .const import NOA_API_URL
from .models import NowOnAirInfo, NowOnAirProgram

# NOA API uses "r3" for FM; SDK uses "fm" everywhere else.
_NOA_CHANNEL_MAP: dict[str, str] = {
    "r1": "r1",
    "r2": "r2",
    "r3": "fm",
}


async def fetch_now_on_air(
    session: aiohttp.ClientSession,
    areakey: str,
) -> dict[str, NowOnAirInfo]:
    """Fetch now-on-air info for all channels in an area."""
    url = NOA_API_URL.format(areakey=areakey)
    data = await api_get_json(session, url)
    return parse_now_on_air(data)


def parse_now_on_air(data: dict[str, Any]) -> dict[str, NowOnAirInfo]:
    """Parse the full NOA JSON response."""
    result: dict[str, NowOnAirInfo] = {}

    for noa_key, sdk_channel_id in _NOA_CHANNEL_MAP.items():
        channel_data = data.get(noa_key)
        if channel_data is None:
            continue

        published_on = channel_data.get("publishedOn", {})
        channel_name = published_on.get("name", "")

        present_data = channel_data.get("present")
        if present_data is None:
            continue

        present = _parse_program(present_data, sdk_channel_id)
        assert present is not None  # guarded by `if present_data is None` above

        result[sdk_channel_id] = NowOnAirInfo(
            channel_id=sdk_channel_id,
            channel_name=channel_name,
            previous=_parse_program(channel_data.get("previous"), sdk_channel_id),
            present=present,
            following=_parse_program(channel_data.get("following"), sdk_channel_id),
        )

    return result


def _parse_program(
    data: dict[str, Any] | None,
    channel_id: str,
) -> NowOnAirProgram | None:
    """Parse a single BroadcastEvent into NowOnAirProgram."""
    if data is None:
        return None

    identifier = data.get("identifierGroup", {})
    about = data.get("about", {})
    part_of_series = about.get("partOfSeries", {})
    logo = part_of_series.get("logo", {})
    main_logo = logo.get("main", {})

    return NowOnAirProgram(
        event_id=identifier.get("broadcastEventId", ""),
        channel_id=channel_id,
        title=data.get("name", ""),
        description=data.get("description", ""),
        series_name=identifier.get("radioSeriesName", ""),
        act=about.get("description", ""),
        start_at=data.get("startDate", ""),
        end_at=data.get("endDate", ""),
        thumbnail_url=main_logo.get("url") or None,
    )
