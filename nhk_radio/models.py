"""Data models for the nhk_radio SDK."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, runtime_checkable


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
    def series_site_id(self) -> str: ...


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
class RadioProgram:
    """A playable radio program (implements Program)."""

    title: str
    description: str
    thumbnail_url: str | None
    series_name: str
    series_site_id: str
    act: str
    channel_id: str
    stream_url: str
    start_at: datetime
    end_at: datetime


@dataclass(frozen=True, slots=True)
class LiveProgram(RadioProgram):
    """A live broadcast program."""

    event_id: str = ""


@dataclass(frozen=True, slots=True)
class OndemandProgram(RadioProgram):
    """An on-demand episode with a playable stream."""

    episode_id: str = ""
    closed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class LiveInfo:
    """Live broadcast info for a single channel (previous/present/following)."""

    channel: Channel
    area: Area
    previous: LiveProgram | None
    present: LiveProgram
    following: LiveProgram | None


@dataclass(frozen=True, slots=True)
class OndemandSeries:
    """An on-demand series catalog entry (implements Program)."""

    title: str
    description: str
    thumbnail_url: str | None
    series_site_id: str
    series_name: str
    radio_broadcast: str
    corner_site_id: str
    corner_name: str = ""


@dataclass(frozen=True, slots=True)
class Genre:
    """An on-demand genre."""

    genre: str
    name: str


Kana = Literal["a", "k", "s", "t", "n", "h", "m", "y", "r", "w"]
