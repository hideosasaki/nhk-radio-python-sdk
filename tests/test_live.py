"""Tests for live.py (areas, channels, and live program parsing)."""

from datetime import datetime, timedelta, timezone

import aiohttp
import pytest
from aioresponses import aioresponses

from nhk_radio.config import parse_config
from nhk_radio.const import NOA_API_URL
from nhk_radio.errors import ApiError, AreaNotFoundError, NetworkError
from nhk_radio.live import (
    fetch_live_programs,
    get_area,
    get_areas,
    get_channels_for_area,
    parse_live_programs,
)
from nhk_radio.models import Area, Channel

JST = timezone(timedelta(hours=9))

_STUB_AREA = Area(
    id="tokyo",
    name="東京",
    areakey="130",
    channels=[
        Channel(id="r1", name="R1", stream_url=""),
        Channel(id="r2", name="R2", stream_url=""),
        Channel(id="fm", name="FM", stream_url=""),
    ],
)


@pytest.fixture
def config(config_xml_bytes: bytes):
    return parse_config(config_xml_bytes)


# --- Area / channel tests ---


def test_get_areas(config) -> None:
    areas = get_areas(config)
    assert len(areas) == 8
    area_ids = {a.id for a in areas}
    assert "tokyo" in area_ids


def test_get_channels_for_area(config) -> None:
    channels = get_channels_for_area(config, "tokyo")
    assert len(channels) == 3
    assert any(ch.id == "r1" for ch in channels)


def test_get_channels_for_area_invalid(config) -> None:
    with pytest.raises(AreaNotFoundError) as exc_info:
        get_channels_for_area(config, "invalid")
    assert "invalid" in str(exc_info.value)
    assert exc_info.value.available


# --- Live program parsing tests ---


def test_parse_live_programs_r3_mapped_to_fm(
    live_programs_json: dict,
) -> None:
    """r3 in API response should be mapped to 'fm' in SDK."""
    result = parse_live_programs(live_programs_json, _STUB_AREA)

    assert len(result) == 3
    assert set(result.keys()) == {"r1", "r2", "fm"}

    fm = result["fm"]
    assert fm.channel.id == "fm"
    assert fm.area.id == "tokyo"
    assert fm.present.channel_id == "fm"


def test_parse_live_programs_present(
    live_programs_json: dict,
) -> None:
    result = parse_live_programs(live_programs_json, _STUB_AREA)

    r1 = result["r1"]
    assert r1.present.title == "野村萬斎のラジオで福袋【ゲスト】中村壱太郎パート２"
    assert r1.present.event_id == "r1-130-2026030969455"
    assert r1.present.series_name == "野村萬斎のラジオで福袋"
    assert r1.present.act == "野村萬斎,【ゲスト】中村壱太郎"
    assert r1.present.start_at == datetime(2026, 3, 9, 20, 5, 0, tzinfo=JST)
    assert r1.present.end_at == datetime(2026, 3, 9, 20, 55, 0, tzinfo=JST)
    assert r1.present.thumbnail_url is not None
    assert r1.present.series_site_id == "1K5J894M9V"
    assert r1.present.stream_url == ""


def test_parse_live_programs_previous_following(
    live_programs_json: dict,
) -> None:
    result = parse_live_programs(live_programs_json, _STUB_AREA)

    r1 = result["r1"]
    assert r1.previous is not None
    assert r1.previous.title == "ニュース"
    assert r1.following is not None
    assert r1.following.title == "ニュース・気象情報"


def test_parse_live_programs_nullable_previous_following(
    live_programs_json: dict,
) -> None:
    result = parse_live_programs(live_programs_json, _STUB_AREA)

    r2 = result["r2"]
    assert r2.previous is None
    assert r2.following is None
    assert r2.present.title == "ＮＨＫ高校講座　政治・経済"


def test_parse_live_programs_thumbnail_none_when_missing() -> None:
    """When logo is empty, thumbnail_url should be None."""
    data = {
        "r1": {
            "present": {
                "name": "Test",
                "description": "",
                "startDate": "",
                "endDate": "",
                "identifierGroup": {
                    "broadcastEventId": "test-id",
                    "radioSeriesName": "Test Series",
                },
                "about": {
                    "description": "",
                    "partOfSeries": {"logo": {}},
                },
            },
            "previous": None,
            "following": None,
            "publishedOn": {"name": "Test Channel"},
        }
    }
    result = parse_live_programs(data, _STUB_AREA)
    assert result["r1"].present.thumbnail_url is None


def test_parse_live_programs_empty() -> None:
    result = parse_live_programs({}, _STUB_AREA)
    assert result == {}


def test_parse_live_programs_skips_missing_present() -> None:
    """Channels without a 'present' field should be skipped."""
    data = {
        "r1": {
            "previous": None,
            "following": None,
            "publishedOn": {"name": "Test"},
        }
    }
    result = parse_live_programs(data, _STUB_AREA)
    assert result == {}


# --- Fetch tests ---


@pytest.mark.asyncio
async def test_fetch_live_programs_http_error() -> None:
    url = NOA_API_URL.format(areakey="130")
    with aioresponses() as m:
        m.get(url, status=500)
        async with aiohttp.ClientSession() as session:
            with pytest.raises(ApiError):
                await fetch_live_programs(session, _STUB_AREA)


@pytest.mark.asyncio
async def test_fetch_live_programs_network_error() -> None:
    url = NOA_API_URL.format(areakey="130")
    with aioresponses() as m:
        m.get(url, exception=aiohttp.ClientError("timeout"))
        async with aiohttp.ClientSession() as session:
            with pytest.raises(NetworkError):
                await fetch_live_programs(session, _STUB_AREA)
