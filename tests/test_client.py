"""Tests for client.py with mocked HTTP."""

import aiohttp
import pytest
from aioresponses import aioresponses

from nhk_radio.client import NhkRadioClient
from nhk_radio.const import CONFIG_URL, NOA_API_URL
from nhk_radio.errors import AreaNotFoundError, ConfigFetchError


@pytest.fixture
def mock_aiohttp():
    with aioresponses() as m:
        yield m


@pytest.mark.asyncio
async def test_lazy_config_load(mock_aiohttp, config_xml_bytes: bytes) -> None:
    """Config should not be fetched at construction time."""
    async with aiohttp.ClientSession() as session:
        client = NhkRadioClient(session, area="tokyo")
        # No request yet
        assert client._config is None

        mock_aiohttp.get(CONFIG_URL, body=config_xml_bytes)
        channels = await client.get_channels()
        assert len(channels) == 3
        assert client._config is not None


@pytest.mark.asyncio
async def test_invalid_area(mock_aiohttp, config_xml_bytes: bytes) -> None:
    mock_aiohttp.get(CONFIG_URL, body=config_xml_bytes)

    async with aiohttp.ClientSession() as session:
        client = NhkRadioClient(session, area="invalid")
        with pytest.raises(AreaNotFoundError):
            await client.get_channels()


@pytest.mark.asyncio
async def test_config_fetch_failure(mock_aiohttp) -> None:
    mock_aiohttp.get(CONFIG_URL, status=500)

    async with aiohttp.ClientSession() as session:
        client = NhkRadioClient(session, area="tokyo")
        with pytest.raises(ConfigFetchError):
            await client.get_channels()


@pytest.mark.asyncio
async def test_get_live_programs_has_stream_url(
    mock_aiohttp, config_xml_bytes: bytes, live_programs_json: dict
) -> None:
    """get_live_programs should return LiveInfo with stream_url from config."""
    mock_aiohttp.get(CONFIG_URL, body=config_xml_bytes)
    mock_aiohttp.get(
        NOA_API_URL.format(areakey="130"),
        payload=live_programs_json,
    )

    async with aiohttp.ClientSession() as session:
        client = NhkRadioClient(session, area="tokyo")
        result = await client.get_live_programs()

        for info in result.values():
            assert info.present.stream_url != ""
            assert info.present.stream_url.endswith(".m3u8")
