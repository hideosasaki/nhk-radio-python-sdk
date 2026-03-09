"""Tests for ondemand.py parsing."""

import aiohttp
import pytest
from aioresponses import aioresponses

from nhk_radio.const import ONDEMAND_NEW_ARRIVALS_URL, ONDEMAND_SERIES_URL
from nhk_radio.errors import NetworkError
from nhk_radio.ondemand import (
    fetch_new_arrivals,
    fetch_series,
    parse_new_arrivals,
    parse_series_detail,
)


def test_parse_new_arrivals(new_arrivals_json: dict) -> None:
    result = parse_new_arrivals(new_arrivals_json)
    assert len(result) > 0

    first = result[0]
    assert first.title
    assert first.site_id
    assert len(first.corners) == 1
    assert first.corners[0].corner_site_id


def test_parse_new_arrivals_radio_broadcast(new_arrivals_json: dict) -> None:
    result = parse_new_arrivals(new_arrivals_json)
    broadcasts = {s.radio_broadcast for s in result}
    # Should have various broadcast values
    assert len(broadcasts) > 1
    # All should be non-empty
    assert all(s.radio_broadcast for s in result)


def test_parse_new_arrivals_has_thumbnail(new_arrivals_json: dict) -> None:
    result = parse_new_arrivals(new_arrivals_json)
    thumbnails = [s.thumbnail_url for s in result if s.thumbnail_url]
    assert len(thumbnails) > 0


def test_parse_series_detail(series_detail_json: dict) -> None:
    result = parse_series_detail(series_detail_json)
    assert result.series_title
    assert result.thumbnail_url
    assert len(result.episodes) > 0

    ep = result.episodes[0]
    assert ep.title
    assert ep.stream_url
    assert ep.stream_url.endswith(".m3u8")


def test_parse_series_detail_episode_fields(series_detail_json: dict) -> None:
    result = parse_series_detail(series_detail_json)
    ep = result.episodes[0]
    assert ep.episode_id
    assert ep.description is not None
    assert ep.onair_date
    assert ep.closed_at
    # Fields inherited from parent
    assert ep.thumbnail_url == result.thumbnail_url
    assert ep.series_name == result.series_title
    assert ep.act is not None


def test_parse_new_arrivals_channel_filter(new_arrivals_json: dict) -> None:
    result = parse_new_arrivals(new_arrivals_json)
    r1_only = [s for s in result if "R1" in s.radio_broadcast.split(",")]
    fm_only = [s for s in result if "FM" in s.radio_broadcast.split(",")]
    assert len(r1_only) > 0
    assert len(fm_only) > 0
    # Each filtered list should be smaller than the full list
    assert len(r1_only) < len(result)
    assert len(fm_only) < len(result)


def test_parse_new_arrivals_empty() -> None:
    result = parse_new_arrivals({"corners": []})
    assert result == []


def test_parse_series_detail_no_episodes() -> None:
    result = parse_series_detail({"title": "Test", "corner_name": "", "episodes": []})
    assert result.series_title == "Test"
    assert result.thumbnail_url is None
    assert result.episodes == []


@pytest.mark.asyncio
async def test_fetch_new_arrivals_connection_error() -> None:
    """Connection errors should raise NetworkError, not ApiError."""
    with aioresponses() as m:
        m.get(ONDEMAND_NEW_ARRIVALS_URL, exception=aiohttp.ClientError("timeout"))
        async with aiohttp.ClientSession() as session:
            with pytest.raises(NetworkError) as exc_info:
                await fetch_new_arrivals(session)
            assert exc_info.value.url == ONDEMAND_NEW_ARRIVALS_URL


@pytest.mark.asyncio
async def test_fetch_series_connection_error() -> None:
    """Connection errors should raise NetworkError, not ApiError."""
    with aioresponses() as m:
        m.get(ONDEMAND_SERIES_URL, exception=aiohttp.ClientError("timeout"))
        async with aiohttp.ClientSession() as session:
            with pytest.raises(NetworkError) as exc_info:
                await fetch_series(session, "site1", "corner1")
            assert exc_info.value.url == ONDEMAND_SERIES_URL


def test_parse_new_arrivals_missing_corners_key() -> None:
    """Missing 'corners' key should raise KeyError."""
    with pytest.raises(KeyError):
        parse_new_arrivals({"other_key": []})


def test_parse_series_detail_missing_episodes_key() -> None:
    """Missing 'episodes' key should raise KeyError."""
    with pytest.raises(KeyError):
        parse_series_detail({"title": "Test", "corner_name": ""})
