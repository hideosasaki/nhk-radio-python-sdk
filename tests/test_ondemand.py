"""Tests for ondemand.py parsing."""

from datetime import datetime

import aiohttp
import pytest
from aioresponses import aioresponses

from nhk_radio.const import ONDEMAND_NEW_ARRIVALS_URL
from nhk_radio.errors import NetworkError
from nhk_radio.ondemand import (
    fetch_ondemand_new_arrivals,
    parse_ondemand_new_arrivals,
    parse_ondemand_programs,
)


def test_parse_ondemand_new_arrivals(new_arrivals_json: dict) -> None:
    result = parse_ondemand_new_arrivals(new_arrivals_json)
    assert len(result) > 0

    first = result[0]
    assert first.title
    assert first.series_site_id
    assert first.corner_site_id


def test_parse_ondemand_programs(series_detail_json: dict) -> None:
    series, programs = parse_ondemand_programs(series_detail_json)

    # Series info
    assert series.title == "大相撲中継"
    assert "NHK大相撲中継" in series.description
    assert series.schedule is not None
    assert series.series_url is not None

    # Episodes
    assert len(programs) > 0
    ep = programs[0]
    assert ep.title
    assert ep.stream_url.endswith(".m3u8")
    assert ep.episode_id
    assert isinstance(ep.start_at, datetime)
    assert isinstance(ep.end_at, datetime)
    assert ep.closed_at is None or isinstance(ep.closed_at, datetime)
    assert ep.series_name
    assert ep.act is not None


def test_parse_ondemand_new_arrivals_empty() -> None:
    result = parse_ondemand_new_arrivals({"corners": []})
    assert result == []


def test_parse_ondemand_programs_no_episodes() -> None:
    data = {"title": "Test", "corner_name": "", "episodes": []}
    series, programs = parse_ondemand_programs(data)
    assert series.title == "Test"
    assert programs == []


@pytest.mark.asyncio
async def test_fetch_ondemand_new_arrivals_connection_error() -> None:
    """Connection errors should raise NetworkError, not ApiError."""
    with aioresponses() as m:
        m.get(ONDEMAND_NEW_ARRIVALS_URL, exception=aiohttp.ClientError("timeout"))
        async with aiohttp.ClientSession() as session:
            with pytest.raises(NetworkError) as exc_info:
                await fetch_ondemand_new_arrivals(session)
            assert exc_info.value.url == ONDEMAND_NEW_ARRIVALS_URL
