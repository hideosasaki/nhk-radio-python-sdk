"""Fetch and parse NHK Radio config_web.xml."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import aiohttp

from .const import CONFIG_URL, REQUEST_TIMEOUT
from .errors import ConfigFetchError
from .models import Area, Channel

_LOGGER = logging.getLogger(__name__)

_CHANNEL_TAG_SUFFIX = "hls"
_CHANNEL_DISPLAY_NAMES: dict[str, str] = {
    "r1": "R1",
    "r2": "R2",
    "fm": "FM",
}


@dataclass(frozen=True, slots=True)
class RadiruConfig:
    """Parsed configuration from config_web.xml."""

    areas: dict[str, Area]


def parse_config(xml_bytes: bytes) -> RadiruConfig:
    """Parse config_web.xml bytes into a RadiruConfig.

    Channels are discovered dynamically by scanning for tags ending in 'hls'.
    This means the SDK automatically adapts when NHK adds or removes channels.
    """
    root = ET.fromstring(xml_bytes)

    areas: dict[str, Area] = {}

    stream_url_el = root.find("stream_url")
    if stream_url_el is None:
        raise ConfigFetchError("Missing <stream_url> element in config XML")

    for data_el in stream_url_el.findall("data"):
        area_id = (data_el.findtext("area") or "").strip()
        area_name = (data_el.findtext("areajp") or "").strip()

        areakey = (data_el.findtext("areakey") or "").strip()

        if not area_id:
            continue

        channels: list[Channel] = []
        for child in data_el:
            tag = child.tag
            if tag.endswith(_CHANNEL_TAG_SUFFIX) and child.text:
                ch_id = tag.removesuffix(_CHANNEL_TAG_SUFFIX)
                ch_name = _CHANNEL_DISPLAY_NAMES.get(ch_id, ch_id.upper())
                channels.append(
                    Channel(id=ch_id, name=ch_name, stream_url=child.text.strip())
                )

        if not channels:
            _LOGGER.warning("Area '%s' has no channels, skipping", area_id)
            continue

        areas[area_id] = Area(
            id=area_id,
            name=area_name,
            areakey=areakey,
            channels=channels,
        )

    if not areas:
        raise ConfigFetchError("No areas found in config XML")

    return RadiruConfig(areas=areas)


async def fetch_config(session: aiohttp.ClientSession) -> RadiruConfig:
    """Fetch config_web.xml from NHK and parse it."""
    try:
        async with session.get(
            CONFIG_URL, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        ) as resp:
            if resp.status != 200:
                raise ConfigFetchError(
                    f"Failed to fetch config: HTTP {resp.status}"
                )
            xml_bytes = await resp.read()
    except aiohttp.ClientError as exc:
        raise ConfigFetchError(f"Failed to fetch config: {exc}") from exc

    try:
        return parse_config(xml_bytes)
    except ConfigFetchError:
        raise
    except (ET.ParseError, KeyError, AttributeError) as exc:
        raise ConfigFetchError(f"Failed to parse config XML: {exc}") from exc
