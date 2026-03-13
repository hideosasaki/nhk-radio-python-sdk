"""Live stream resolution and program information via the NOA API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import aiohttp

from ._api import api_get_json
from .config import RadiruConfig
from .const import EPOCH, NOA_API_URL
from .errors import AreaNotFoundError
from .models import Area, Channel, LiveInfo, LiveProgram

# NOA API uses "r3" for FM; SDK uses "fm" everywhere else.
_NOA_CHANNEL_MAP: dict[str, str] = {
    "r1": "r1",
    "r2": "r2",
    "r3": "fm",
}


# --- Area / channel helpers ---


def get_areas(config: RadiruConfig) -> list[Area]:
    """Return all available areas."""
    return list(config.areas.values())


def get_area(config: RadiruConfig, area_id: str) -> Area:
    """Look up an area by id, raising AreaNotFoundError if missing."""
    area = config.areas.get(area_id)
    if area is None:
        raise AreaNotFoundError(area_id, list(config.areas.keys()))
    return area


def get_channels_for_area(config: RadiruConfig, area_id: str) -> list[Channel]:
    """Return channels for an area."""
    return get_area(config, area_id).channels


# --- Live program fetching / parsing ---


async def fetch_live_programs(
    session: aiohttp.ClientSession,
    area: Area,
) -> dict[str, LiveInfo]:
    """Fetch live program info for all channels in an area."""
    url = NOA_API_URL.format(areakey=area.areakey)
    data = await api_get_json(session, url)
    return parse_live_programs(data, area)


def parse_live_programs(data: dict[str, Any], area: Area) -> dict[str, LiveInfo]:
    """Parse the full NOA JSON response."""
    result: dict[str, LiveInfo] = {}

    for noa_key, sdk_channel_id in _NOA_CHANNEL_MAP.items():
        channel_data = data.get(noa_key)
        if channel_data is None:
            continue

        present_data = channel_data.get("present")
        if present_data is None:
            continue

        channel = area.get_channel(sdk_channel_id)
        if channel is None:
            continue

        stream_url = channel.stream_url

        present = _parse_live_program(present_data, sdk_channel_id, stream_url)
        if present is None:
            continue

        result[sdk_channel_id] = LiveInfo(
            channel=channel,
            area=area,
            previous=_parse_live_program(
                channel_data.get("previous"), sdk_channel_id, stream_url
            ),
            present=present,
            following=_parse_live_program(
                channel_data.get("following"), sdk_channel_id, stream_url
            ),
        )

    return result


def _parse_live_program(
    data: dict[str, Any] | None,
    channel_id: str,
    stream_url: str,
) -> LiveProgram | None:
    """Parse a single BroadcastEvent into LiveProgram."""
    if data is None:
        return None

    identifier = data.get("identifierGroup", {})
    about = data.get("about", {})
    part_of_series = about.get("partOfSeries", {})
    logo = part_of_series.get("logo", {})
    main_logo = logo.get("main", {})

    return LiveProgram(
        title=data.get("name", ""),
        description=data.get("description", ""),
        thumbnail_url=main_logo.get("url") or None,
        series_name=identifier.get("radioSeriesName", ""),
        series_site_id=identifier.get("radioSeriesId", ""),
        act=about.get("description", ""),
        channel_id=channel_id,
        stream_url=stream_url,
        start_at=_parse_datetime(data.get("startDate", "")),
        end_at=_parse_datetime(data.get("endDate", "")),
        event_id=identifier.get("broadcastEventId") or None,
    )


def _parse_datetime(value: str) -> datetime:
    """Parse an ISO 8601 string, returning epoch on failure."""
    if not value:
        return EPOCH
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return EPOCH
