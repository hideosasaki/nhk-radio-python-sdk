"""Data models for the nhk_radio SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class Program(Protocol):
    """Common interface for programs (live and on-demand)."""

    @property
    def title(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def thumbnail_url(self) -> str | None: ...

    @property
    def series_name(self) -> str: ...

    @property
    def act(self) -> str: ...


@dataclass(frozen=True, slots=True)
class Channel:
    """A radio channel available in an area."""

    id: str
    name: str
    stream_url: str


@dataclass(frozen=True, slots=True)
class Area:
    """A broadcast area with its available channels."""

    id: str
    name: str
    areakey: str
    channels: list[Channel]

    def get_channel(self, channel_id: str) -> Channel | None:
        """Look up a channel by id."""
        for ch in self.channels:
            if ch.id == channel_id:
                return ch
        return None


@dataclass(frozen=True, slots=True)
class NowOnAirProgram:
    """A program currently on air (or adjacent: previous/following)."""

    event_id: str
    channel_id: str
    title: str
    description: str
    series_name: str
    act: str
    start_at: str
    end_at: str
    thumbnail_url: str | None


@dataclass(frozen=True, slots=True)
class NowOnAirInfo:
    """Now-on-air information for a single channel."""

    channel_id: str
    channel_name: str
    previous: NowOnAirProgram | None
    present: NowOnAirProgram
    following: NowOnAirProgram | None


@dataclass(frozen=True, slots=True)
class OndemandCorner:
    """A corner (sub-section) of an on-demand series."""

    corner_id: str
    corner_site_id: str
    title: str
    series_site_id: str


@dataclass(frozen=True, slots=True)
class OndemandSeries:
    """An on-demand series from new arrivals."""

    series_id: str
    site_id: str
    title: str
    description: str
    radio_broadcast: str  # e.g. "R1", "FM", "R1,FM"
    thumbnail_url: str | None
    corners: list[OndemandCorner]


@dataclass(frozen=True, slots=True)
class OndemandEpisode:
    """A single on-demand episode with a playable stream."""

    episode_id: str
    title: str
    description: str
    stream_url: str
    onair_date: str
    closed_at: str
    thumbnail_url: str | None
    series_name: str
    act: str


@dataclass(frozen=True, slots=True)
class OndemandSeriesDetail:
    """Full detail for a series corner, including its episodes."""

    series_title: str
    corner_title: str
    thumbnail_url: str | None
    episodes: list[OndemandEpisode]
