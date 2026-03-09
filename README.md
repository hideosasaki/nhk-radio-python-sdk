# nhk-radio-python-sdk

NHKラジオ（らじる★らじる）の配信URL取得のための非同期Python SDK。

## 機能

- **ライブストリーム** — 地域・チャンネル指定でHLS配信URLを取得
- **放送中の番組情報** — 現在放送中の番組名・出演者・サムネイル等を取得、番組切り替わり通知
- **聞き逃し（オンデマンド）** — 番組の聞き逃し配信を検索・再生URLを取得
- **共通インターフェイス** — ライブ・オンデマンドの番組情報を `Program` Protocol で統一的に扱える

チャンネル構成は `config_web.xml` から動的に検出するため、NHKのチャンネル変更（R2廃止等）にも自動対応します。

## インストール

```bash
pip install nhk-radio-python-sdk
```

または開発用:

```bash
git clone https://github.com/hideosasaki/nhk-radio-python-sdk.git
cd nhk-radio-python-sdk
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## クイックスタート

```python
import asyncio
import aiohttp
from nhk_radio import NhkRadioClient

async def main():
    async with aiohttp.ClientSession() as session:
        client = NhkRadioClient(session, area="tokyo")

        # 利用可能なチャンネル一覧
        channels = await client.get_channels()
        for ch in channels:
            print(f"{ch.name}: {ch.stream_url}")

asyncio.run(main())
```

## API リファレンス

### `NhkRadioClient`

```python
NhkRadioClient(session: aiohttp.ClientSession, *, area: str = "tokyo")
```

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `session` | `aiohttp.ClientSession` | — | HTTPセッション |
| `area` | `str` | `"tokyo"` | 対象地域ID |

プロパティ: `area: str` — 設定された地域ID

---

### ライブストリーム

#### `get_areas() -> list[Area]`

全地域の一覧を取得します。

#### `get_channels() -> list[Channel]`

設定地域のチャンネル一覧を取得します。

#### `get_stream_url(channel_id: str) -> str`

指定チャンネルのHLS配信URLを取得します。

```python
# 特定チャンネルの配信URLを取得
url = await client.get_stream_url("r1")  # NHKラジオ第1
url = await client.get_stream_url("fm")  # NHK-FM

# 全地域の一覧
areas = await client.get_areas()
for area in areas:
    print(f"{area.name} ({area.id}): {[ch.id for ch in area.channels]}")
```

利用可能な地域: `sapporo`, `sendai`, `tokyo`, `nagoya`, `osaka`, `hiroshima`, `matsuyama`, `fukuoka`

---

### 放送中の番組情報（Now On Air）

#### `get_now_on_air() -> dict[str, NowOnAirInfo]`

全チャンネルの放送中番組情報を取得します。キーはチャンネルID（`"r1"`, `"r2"`, `"fm"`）。

```python
now = await client.get_now_on_air()
for channel_id, info in now.items():
    program = info.present
    print(f"[{info.channel_name}] {program.title}")
    print(f"  シリーズ: {program.series_name}")
    print(f"  出演: {program.act}")
    print(f"  {program.start_at} 〜 {program.end_at}")

# 前後の番組も取得可能
r1 = now["r1"]
if r1.previous:
    print(f"前の番組: {r1.previous.title}")
if r1.following:
    print(f"次の番組: {r1.following.title}")
```

#### `listen_now_on_air(channel_id: str | None = None, *, interval: float = 60.0) -> AsyncGenerator[NowOnAirInfo]`

番組が変わるたびに通知する async iterator です。停止するには `asyncio.Task.cancel()` を使います。

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `channel_id` | `str \| None` | `None` | 監視するチャンネル（`None` で全チャンネル） |
| `interval` | `float` | `60.0` | ポーリング間隔（秒） |

```python
# 全チャンネルを監視（60秒間隔でポーリング）
async for info in client.listen_now_on_air(interval=60):
    print(f"番組が変わりました: [{info.channel_name}] {info.present.title}")

# 特定チャンネルのみ監視
async for info in client.listen_now_on_air(channel_id="fm", interval=30):
    print(f"FM: {info.present.title}")
```

---

### 聞き逃し（オンデマンド）

#### `get_ondemand_new_arrivals(*, channel: str | None = None, filter_fn: Callable[[OndemandSeries], bool] | None = None) -> list[OndemandSeries]`

聞き逃し新着番組を取得します。

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `channel` | `str \| None` | `None` | チャンネルで絞り込み（例: `"r1"`, `"fm"`） |
| `filter_fn` | `Callable \| None` | `None` | カスタムフィルタ関数 |

```python
# 新着番組の一覧
series_list = await client.get_ondemand_new_arrivals()
for series in series_list:
    print(f"{series.title} ({series.site_id})")

# チャンネルで絞り込み
fm_series = await client.get_ondemand_new_arrivals(channel="fm")

# カスタムフィルタ（キーワード検索）
news = await client.get_ondemand_new_arrivals(
    filter_fn=lambda s: "ニュース" in s.title
)

# 正規表現
import re
pattern = re.compile(r"英語|英会話")
english = await client.get_ondemand_new_arrivals(
    filter_fn=lambda s: pattern.search(s.title) is not None
)

# 組み合わせ
fm_classic = await client.get_ondemand_new_arrivals(
    channel="fm",
    filter_fn=lambda s: "クラシック" in s.title,
)
```

#### `get_ondemand_series(site_id: str, corner_site_id: str) -> OndemandSeriesDetail`

番組のエピソード一覧と再生URLを取得します。

```python
detail = await client.get_ondemand_series(
    site_id=series_list[0].site_id,
    corner_site_id=series_list[0].corners[0].corner_site_id,
)
for ep in detail.episodes:
    print(f"  {ep.title}: {ep.stream_url}")
```

---

### 設定の再読み込み

#### `refresh_config() -> None`

NHKは配信URLを不定期に変更します。長時間稼働するアプリケーションでは定期的に設定を再取得してください。初回は自動実行されます。

```python
await client.refresh_config()
```

---

### データモデル

#### `Program` (Protocol)

ライブ番組（`NowOnAirProgram`）とオンデマンドエピソード（`OndemandEpisode`）の共通インターフェイス。統一的に扱えます。

| フィールド | 型 | 説明 |
|---|---|---|
| `title` | `str` | 番組タイトル |
| `description` | `str` | 番組概要 |
| `thumbnail_url` | `str \| None` | サムネイルURL |
| `series_name` | `str` | シリーズ名 |
| `act` | `str` | 出演者 |

```python
from nhk_radio import Program

def show_program(p: Program) -> None:
    print(f"{p.series_name}: {p.title}")
    print(f"  出演: {p.act}")
    print(f"  サムネイル: {p.thumbnail_url}")

# ライブ番組でもオンデマンドでも同じように扱える
show_program(now["r1"].present)
show_program(detail.episodes[0])
```

#### `Area`

| フィールド | 型 | 説明 |
|---|---|---|
| `id` | `str` | 地域ID（例: `"tokyo"`） |
| `name` | `str` | 地域名 |
| `areakey` | `str` | APIキー |
| `channels` | `list[Channel]` | 利用可能なチャンネル |

メソッド: `get_channel(channel_id: str) -> Channel | None`

#### `Channel`

| フィールド | 型 | 説明 |
|---|---|---|
| `id` | `str` | チャンネルID（例: `"r1"`, `"fm"`） |
| `name` | `str` | チャンネル名 |
| `stream_url` | `str` | HLS配信URL |

#### `NowOnAirInfo`

| フィールド | 型 | 説明 |
|---|---|---|
| `channel_id` | `str` | チャンネルID |
| `channel_name` | `str` | チャンネル名 |
| `previous` | `NowOnAirProgram \| None` | 前の番組 |
| `present` | `NowOnAirProgram` | 現在の番組 |
| `following` | `NowOnAirProgram \| None` | 次の番組 |

#### `NowOnAirProgram`

`Program` Protocol を実装。

| フィールド | 型 | 説明 |
|---|---|---|
| `event_id` | `str` | イベントID |
| `channel_id` | `str` | チャンネルID |
| `title` | `str` | 番組タイトル |
| `description` | `str` | 番組概要 |
| `series_name` | `str` | シリーズ名 |
| `act` | `str` | 出演者 |
| `start_at` | `str` | 放送開始時刻 |
| `end_at` | `str` | 放送終了時刻 |
| `thumbnail_url` | `str \| None` | サムネイルURL |

#### `OndemandSeries`

| フィールド | 型 | 説明 |
|---|---|---|
| `series_id` | `str` | シリーズID |
| `site_id` | `str` | サイトID |
| `title` | `str` | シリーズタイトル |
| `description` | `str` | 概要 |
| `radio_broadcast` | `str` | 放送チャンネル（例: `"R1"`, `"FM"`） |
| `thumbnail_url` | `str \| None` | サムネイルURL |
| `corners` | `list[OndemandCorner]` | コーナー一覧 |

#### `OndemandCorner`

| フィールド | 型 | 説明 |
|---|---|---|
| `corner_id` | `str` | コーナーID |
| `corner_site_id` | `str` | コーナーサイトID |
| `title` | `str` | コーナータイトル |
| `series_site_id` | `str` | シリーズサイトID |

#### `OndemandSeriesDetail`

| フィールド | 型 | 説明 |
|---|---|---|
| `series_title` | `str` | シリーズタイトル |
| `corner_title` | `str` | コーナータイトル |
| `thumbnail_url` | `str \| None` | サムネイルURL |
| `episodes` | `list[OndemandEpisode]` | エピソード一覧 |

#### `OndemandEpisode`

`Program` Protocol を実装。

| フィールド | 型 | 説明 |
|---|---|---|
| `episode_id` | `str` | エピソードID |
| `title` | `str` | エピソードタイトル |
| `description` | `str` | 概要 |
| `stream_url` | `str` | HLS配信URL |
| `onair_date` | `str` | 放送日 |
| `closed_at` | `str` | 配信終了日時 |
| `thumbnail_url` | `str \| None` | サムネイルURL |
| `series_name` | `str` | シリーズ名 |
| `act` | `str` | 出演者 |

---

### 例外

すべて `NhkRadioError` を継承しています。

| 例外 | 説明 | 属性 |
|---|---|---|
| `NhkRadioError` | 基底例外クラス | — |
| `ConfigFetchError` | config_web.xml の取得・パース失敗 | — |
| `AreaNotFoundError` | 指定した地域が存在しない | `area_id: str`, `available: list[str]` |
| `ChannelNotFoundError` | 指定したチャンネルが存在しない | `channel_id: str`, `available: list[str]` |
| `ApiError` | APIリクエスト失敗 | `status: int`, `url: str` |
| `NetworkError` | ネットワーク接続失敗 | `url: str` |

```python
from nhk_radio import NhkRadioError, ConfigFetchError, AreaNotFoundError, ChannelNotFoundError

try:
    url = await client.get_stream_url("r1")
except ConfigFetchError:
    # config_web.xml の取得・パースに失敗
    pass
except AreaNotFoundError as e:
    # 指定した地域が存在しない
    print(f"利用可能: {e.available}")
except ChannelNotFoundError as e:
    # 指定したチャンネルが存在しない
    print(f"利用可能: {e.available}")
except NhkRadioError:
    # その他のSDKエラー
    pass
```

## Home Assistant での利用

このSDKは Home Assistant Custom Integration から利用することを想定しています。

```python
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from nhk_radio import NhkRadioClient

async def async_setup_entry(hass, entry):
    session = async_get_clientsession(hass)
    client = NhkRadioClient(session, area=entry.data["area"])
    # client を使って media_player エンティティを構築
```

## 開発

```bash
# テスト
pytest -v

# 型チェック
mypy nhk_radio

# リント
ruff check nhk_radio
```

## ライセンス

Apache License 2.0
