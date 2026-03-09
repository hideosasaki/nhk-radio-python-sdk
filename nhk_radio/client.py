"""NHK Radio client - main entry point for the SDK."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Callable

import aiohttp

from .config import RadiruConfig, fetch_config
from .const import DEFAULT_AREA
from .errors import ConfigFetchError, NhkRadioError
from .live import get_area, get_areas as _get_areas
from .live import get_channels_for_area, get_stream_url
from .models import (
    Area,
    Channel,
    NowOnAirInfo,
    OndemandSeries,
    OndemandSeriesDetail,
)
from .nowonair import fetch_now_on_air
from .ondemand import fetch_new_arrivals, fetch_series

_LOGGER = logging.getLogger(__name__)


class NhkRadioClient:
    """Async client for NHK Radio (らじる★らじる)."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        area: str = DEFAULT_AREA,
    ) -> None:
        self._session = session
        self._area = area
        self._config: RadiruConfig | None = None

    @property
    def area(self) -> str:
        """Return the configured area."""
        return self._area

    async def _ensure_config(self) -> RadiruConfig:
        """Lazy-load config on first access."""
        if self._config is None:
            await self.refresh_config()
        assert self._config is not None
        return self._config

    async def refresh_config(self) -> None:
        """Fetch config_web.xml and rebuild internal state.

        Called automatically on first use; call manually to force refresh.
        """
        try:
            self._config = await fetch_config(self._session)
        except ConfigFetchError:
            raise
        except Exception as exc:
            raise ConfigFetchError(f"Failed to load config: {exc}") from exc

    # --- Live streams ---

    async def get_areas(self) -> list[Area]:
        """Return all available areas."""
        config = await self._ensure_config()
        return _get_areas(config)

    async def get_channels(self) -> list[Channel]:
        """Return channels available in the client's area."""
        config = await self._ensure_config()
        return get_channels_for_area(config, self._area)

    async def get_stream_url(self, channel_id: str) -> str:
        """Return the HLS m3u8 URL for a live channel."""
        config = await self._ensure_config()
        return get_stream_url(config, self._area, channel_id)

    # --- On-demand (聞き逃し) ---

    async def get_ondemand_new_arrivals(
        self,
        *,
        channel: str | None = None,
        filter_fn: Callable[[OndemandSeries], bool] | None = None,
    ) -> list[OndemandSeries]:
        """Return newly arrived on-demand series.

        Args:
            channel: Filter by channel id (e.g. "r1", "fm").
                     Matches against the radio_broadcast field
                     which may contain multiple channels (e.g. "R1,FM").
            filter_fn: Custom filter function applied to each series.
                       Useful for keyword search, regex matching, etc.
        """
        result = await fetch_new_arrivals(self._session)
        if channel is not None:
            ch_upper = channel.upper()
            result = [
                s for s in result
                if ch_upper in s.radio_broadcast.upper().split(",")
            ]
        if filter_fn is not None:
            result = [s for s in result if filter_fn(s)]
        return result

    async def get_ondemand_series(
        self, site_id: str, corner_site_id: str
    ) -> OndemandSeriesDetail:
        """Return episodes for a specific on-demand series corner."""
        return await fetch_series(self._session, site_id, corner_site_id)

    # --- Now on air (NOA) ---

    async def get_now_on_air(self) -> dict[str, NowOnAirInfo]:
        """Return now-on-air program info for all channels.

        Keys are SDK channel ids ("r1", "r2", "fm").
        """
        config = await self._ensure_config()
        area = get_area(config, self._area)
        return await fetch_now_on_air(self._session, area.areakey)

    async def watch_now_on_air(
        self,
        channel_id: str | None = None,
        *,
        interval: float = 60.0,
    ) -> AsyncGenerator[NowOnAirInfo, None]:
        """Yield NowOnAirInfo whenever the current program changes.

        Args:
            channel_id: Watch a specific channel, or None for all.
            interval: Polling interval in seconds (default: 60).

        Yields:
            NowOnAirInfo each time the present program changes
            (detected by event_id change).
        """
        # Resolve areakey once before the loop to avoid repeated config lookups.
        config = await self._ensure_config()
        areakey = get_area(config, self._area).areakey

        last_event_ids: dict[str, str] = {}

        while True:
            try:
                all_info = await fetch_now_on_air(self._session, areakey)
            except NhkRadioError as exc:
                _LOGGER.warning("Failed to fetch now-on-air info: %s", exc)
                await asyncio.sleep(interval)
                continue

            if channel_id is not None:
                targets = [all_info[channel_id]] if channel_id in all_info else []
            else:
                targets = list(all_info.values())

            for info in targets:
                current_id = info.present.event_id
                prev_id = last_event_ids.get(info.channel_id)
                if prev_id != current_id:
                    last_event_ids[info.channel_id] = current_id
                    yield info

            await asyncio.sleep(interval)

