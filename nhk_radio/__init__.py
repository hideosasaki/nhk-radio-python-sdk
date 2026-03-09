"""NHK Radio (らじる★らじる) Python SDK."""

from .client import NhkRadioClient
from .errors import (
    ApiError,
    AreaNotFoundError,
    ChannelNotFoundError,
    ConfigFetchError,
    NetworkError,
    NhkRadioError,
)
from .models import (
    Area,
    Channel,
    NowOnAirInfo,
    NowOnAirProgram,
    OndemandCorner,
    OndemandEpisode,
    OndemandSeries,
    OndemandSeriesDetail,
    Program,
)

__all__ = [
    "ApiError",
    "Area",
    "AreaNotFoundError",
    "Channel",
    "ChannelNotFoundError",
    "ConfigFetchError",
    "NetworkError",
    "NhkRadioClient",
    "NhkRadioError",
    "NowOnAirInfo",
    "NowOnAirProgram",
    "OndemandCorner",
    "OndemandEpisode",
    "OndemandSeries",
    "OndemandSeriesDetail",
    "Program",
]
