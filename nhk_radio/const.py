"""Constants for the nhk_radio SDK."""

CONFIG_URL = "https://www.nhk.or.jp/radio/config/config_web.xml"
ONDEMAND_NEW_ARRIVALS_URL = (
    "https://www.nhk.or.jp/radio-api/app/v1/web/ondemand/corners/new_arrivals"
)
ONDEMAND_SERIES_URL = (
    "https://www.nhk.or.jp/radio-api/app/v1/web/ondemand/series"
)
NOA_API_URL = "https://api.nhk.jp/r7/pg/now/radio/{areakey}/now.json"
DEFAULT_AREA = "tokyo"
REQUEST_TIMEOUT = 10  # seconds
