"""NHK Radio client - main entry point for the SDK."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Callable
from dataclasses import replace
from datetime import UTC, date, datetime

import aiohttp

from .config import RadiruConfig, fetch_config
from .const import DEFAULT_AREA
from .errors import ConfigFetchError, NhkRadioError
from .live import fetch_live_programs, get_area, get_channels_for_area
from .live import get_areas as _get_areas
from .models import (
    Area,
    Channel,
    Genre,
    Kana,
    LiveInfo,
    OndemandProgram,
    OndemandSeries,
)
from .ondemand import (
    fetch_genres,
    fetch_ondemand_by_date,
    fetch_ondemand_by_genre,
    fetch_ondemand_by_kana,
    fetch_ondemand_new_arrivals,
    fetch_ondemand_programs,
    fetch_ondemand_search,
)

_LOGGER = logging.getLogger(__name__)

_REFRESH_DELAY = 60  # Seconds to wait before fetching updated following info
_FALLBACK_DELAY = 3600  # Seconds to wait when following is unavailable


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
            await self.refresh()
        assert self._config is not None
        return self._config

    async def refresh(self) -> None:
        """Fetch config_web.xml and rebuild internal state.

        Called automatically on first use; call manually to force refresh.
        """
        try:
            self._config = await fetch_config(self._session)
        except ConfigFetchError:
            raise
        except (KeyError, AttributeError, TypeError) as exc:
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
        """
        result = await fetch_ondemand_new_arrivals(self._session)
        if channel is not None:
            ch_upper = channel.upper()
            result = [
                s for s in result
                if ch_upper in s.radio_broadcast.upper().split(",")
            ]
        if filter_fn is not None:
            result = [s for s in result if filter_fn(s)]
        return result

    async def get_ondemand_programs(
        self, series_site_id: str, corner_site_id: str
    ) -> list[OndemandProgram]:
        """Return episodes for a specific on-demand series corner."""
        return await fetch_ondemand_programs(
            self._session, series_site_id, corner_site_id
        )

    async def search_ondemand(
        self, keyword: str
    ) -> list[OndemandSeries]:
        """Search on-demand series by keyword."""
        return await fetch_ondemand_search(self._session, keyword)

    async def get_genres(self) -> list[Genre]:
        """Return the list of on-demand genres."""
        return await fetch_genres(self._session)

    async def get_ondemand_by_genre(
        self, genre: str
    ) -> list[OndemandSeries]:
        """Return on-demand series filtered by genre."""
        return await fetch_ondemand_by_genre(self._session, genre)

    async def get_ondemand_by_kana(
        self, kana: Kana
    ) -> list[OndemandSeries]:
        """Return on-demand series filtered by kana initial."""
        return await fetch_ondemand_by_kana(self._session, kana)

    async def get_ondemand_by_date(
        self, onair_date: date
    ) -> list[OndemandSeries]:
        """Return on-demand corners by broadcast date."""
        return await fetch_ondemand_by_date(
            self._session, onair_date.strftime("%Y%m%d")
        )

    # --- Live programs ---

    async def get_live_programs(self) -> dict[str, LiveInfo]:
        """Return live program info for all channels.

        Keys are SDK channel ids ("r1", "r2", "fm").
        """
        config = await self._ensure_config()
        area = get_area(config, self._area)
        return await fetch_live_programs(self._session, area)

    async def on_live_program_change(
        self,
        channel_id: str | None = None,
    ) -> AsyncGenerator[LiveInfo, None]:
        """Yield LiveInfo whenever the current program changes.

        Instead of polling at a fixed interval, this method sleeps until the
        current program's end time and then yields the previously fetched
        ``following`` program.  An API call is made shortly after each
        transition to refresh the next ``following`` info.

        Args:
            channel_id: Listen to a specific channel, or None for all.

        Yields:
            LiveInfo each time the present program changes.
        """
        config = await self._ensure_config()
        area = get_area(config, self._area)

        last_event_ids: dict[str, str | None] = {}
        cache: dict[str, LiveInfo] = {}

        while True:
            # --- Fetch phase: get current info from API ---
            try:
                all_info = await fetch_live_programs(self._session, area)
            except NhkRadioError as exc:
                _LOGGER.warning("Failed to fetch live programs: %s", exc)
                await asyncio.sleep(_REFRESH_DELAY)
                continue

            if channel_id is not None:
                targets = (
                    {channel_id: all_info[channel_id]}
                    if channel_id in all_info
                    else {}
                )
            else:
                targets = all_info

            for ch_id, info in targets.items():
                cache[ch_id] = info
                current_id = info.present.event_id
                if last_event_ids.get(ch_id) != current_id:
                    last_event_ids[ch_id] = current_id
                    yield info

            # --- Sleep phase: wait until the earliest program ends ---
            earliest_end = self._earliest_end_at(cache)
            if earliest_end is None:
                await asyncio.sleep(_FALLBACK_DELAY)
                continue

            delay = (earliest_end - datetime.now(UTC)).total_seconds()
            if delay > 0:
                await asyncio.sleep(delay)

            # --- Transition phase: yield cached following programs ---
            now = datetime.now(UTC)
            new_cache: dict[str, LiveInfo] = {}
            for ch_id, info in cache.items():
                if info.present.end_at > now:
                    new_cache[ch_id] = info
                    continue

                if info.following is None:
                    continue

                transitioned = replace(
                    info,
                    previous=info.present,
                    present=info.following,
                    following=None,
                )
                new_cache[ch_id] = transitioned
                last_event_ids[ch_id] = transitioned.present.event_id
                yield transitioned

            cache = new_cache

            # Wait before refreshing following info from API
            await asyncio.sleep(_REFRESH_DELAY)

    @staticmethod
    def _earliest_end_at(cache: dict[str, LiveInfo]) -> datetime | None:
        """Return the earliest present.end_at across cached channels."""
        return min(
            (info.present.end_at for info in cache.values()),
            default=None,
        )
