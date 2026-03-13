"""Constants for the nhk_radio SDK."""

from datetime import UTC, datetime

# Sentinel for missing or invalid datetime fields.
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

CONFIG_URL = "https://www.nhk.or.jp/radio/config/config_web.xml"
ONDEMAND_NEW_ARRIVALS_URL = (
    "https://www.nhk.or.jp/radio-api/app/v1/web/ondemand/corners/new_arrivals"
)
ONDEMAND_SERIES_URL = (
    "https://www.nhk.or.jp/radio-api/app/v1/web/ondemand/series"
)
ONDEMAND_SERIES_SEARCH_URL = (
    "https://www.nhk.or.jp/radio-api/app/v1/web/ondemand/series/search"
)
ONDEMAND_SERIES_GENRES_URL = (
    "https://www.nhk.or.jp/radio-api/app/v1/web/ondemand/series/genres"
)
ONDEMAND_CORNERS_URL = (
    "https://www.nhk.or.jp/radio-api/app/v1/web/ondemand/corners"
)
NOA_API_URL = "https://api.nhk.jp/r7/pg/now/radio/{areakey}/now.json"
DEFAULT_AREA = "tokyo"
REQUEST_TIMEOUT = 10  # seconds
