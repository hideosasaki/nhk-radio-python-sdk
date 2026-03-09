"""Tests for nowonair.py parsing and fetching."""

import aiohttp
import pytest
from aioresponses import aioresponses

from nhk_radio.const import NOA_API_URL
from nhk_radio.errors import ApiError, NetworkError
from nhk_radio.nowonair import fetch_now_on_air, parse_now_on_air


@pytest.fixture
def now_on_air_json() -> dict:
    import json
    from pathlib import Path

    return json.loads(
        (Path(__file__).parent / "fixtures" / "now_on_air.json").read_text()
    )


def test_parse_now_on_air(now_on_air_json: dict) -> None:
    result = parse_now_on_air(now_on_air_json)

    assert len(result) == 3
    assert set(result.keys()) == {"r1", "r2", "fm"}


def test_parse_now_on_air_r3_mapped_to_fm(now_on_air_json: dict) -> None:
    """r3 in API response should be mapped to 'fm' in SDK."""
    result = parse_now_on_air(now_on_air_json)

    fm = result["fm"]
    assert fm.channel_id == "fm"
    assert fm.channel_name == "NHK FM放送"
    assert fm.present.channel_id == "fm"


def test_parse_now_on_air_present(now_on_air_json: dict) -> None:
    result = parse_now_on_air(now_on_air_json)

    r1 = result["r1"]
    assert r1.present.title == "野村萬斎のラジオで福袋【ゲスト】中村壱太郎パート２"
    assert r1.present.event_id == "r1-130-2026030969455"
    assert r1.present.series_name == "野村萬斎のラジオで福袋"
    assert r1.present.act == "野村萬斎，【ゲスト】中村壱太郎"
    assert r1.present.start_at == "2026-03-09T20:05:00+09:00"
    assert r1.present.end_at == "2026-03-09T20:55:00+09:00"
    assert r1.present.thumbnail_url is not None


def test_parse_now_on_air_previous_following(now_on_air_json: dict) -> None:
    result = parse_now_on_air(now_on_air_json)

    r1 = result["r1"]
    assert r1.previous is not None
    assert r1.previous.title == "ニュース"
    assert r1.following is not None
    assert r1.following.title == "ニュース・気象情報"


def test_parse_now_on_air_nullable_previous_following(now_on_air_json: dict) -> None:
    result = parse_now_on_air(now_on_air_json)

    r2 = result["r2"]
    assert r2.previous is None
    assert r2.following is None
    assert r2.present.title == "ＮＨＫ高校講座　政治・経済"


def test_parse_now_on_air_thumbnail_none_when_missing() -> None:
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
    result = parse_now_on_air(data)
    assert result["r1"].present.thumbnail_url is None


def test_parse_now_on_air_empty() -> None:
    result = parse_now_on_air({})
    assert result == {}


def test_parse_now_on_air_skips_missing_present() -> None:
    """Channels without a 'present' field should be skipped."""
    data = {
        "r1": {
            "previous": None,
            "following": None,
            "publishedOn": {"name": "Test"},
        }
    }
    result = parse_now_on_air(data)
    assert result == {}


@pytest.mark.asyncio
async def test_fetch_now_on_air_success(now_on_air_json: dict) -> None:
    url = NOA_API_URL.format(areakey="130")
    with aioresponses() as m:
        m.get(url, payload=now_on_air_json)
        async with aiohttp.ClientSession() as session:
            result = await fetch_now_on_air(session, "130")
            assert len(result) == 3
            assert "r1" in result


@pytest.mark.asyncio
async def test_fetch_now_on_air_http_error() -> None:
    url = NOA_API_URL.format(areakey="130")
    with aioresponses() as m:
        m.get(url, status=500)
        async with aiohttp.ClientSession() as session:
            with pytest.raises(ApiError):
                await fetch_now_on_air(session, "130")


@pytest.mark.asyncio
async def test_fetch_now_on_air_network_error() -> None:
    url = NOA_API_URL.format(areakey="130")
    with aioresponses() as m:
        m.get(url, exception=aiohttp.ClientError("timeout"))
        async with aiohttp.ClientSession() as session:
            with pytest.raises(NetworkError):
                await fetch_now_on_air(session, "130")
