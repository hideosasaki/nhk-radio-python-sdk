# nhk-radio-python

NHKラジオ（らじる★らじる）の配信URL取得のための非同期Pythonクライアント。

## 機能

- **ライブストリーム** — 地域・チャンネル指定でHLS配信URLを取得
- **放送中の番組情報** — 現在放送中の番組名・出演者・サムネイル等を取得、番組切り替わり通知
- **聞き逃し（オンデマンド）** — 新着・検索・ジャンル・五十音・日付別で番組を検索し、再生URLを取得

チャンネル構成は `config_web.xml` から動的に検出するため、NHKのチャンネル変更（R2廃止等）にも自動対応できるかもしれません。

## インストール

```bash
pip install nhk-radio-python
```

または開発用:

```bash
git clone https://github.com/hideosasaki/nhk-radio-python.git
cd nhk-radio-python
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

設定地域のチャンネル一覧を取得します。各 `Channel` には `stream_url`（HLS配信URL）が含まれます。

```python
# チャンネル一覧と配信URL
channels = await client.get_channels()
for ch in channels:
    print(f"{ch.name}: {ch.stream_url}")

# 全地域の一覧
areas = await client.get_areas()
for area in areas:
    print(f"{area.name} ({area.id}): {[ch.id for ch in area.channels]}")
```

利用可能な地域: `sapporo`, `sendai`, `tokyo`, `nagoya`, `osaka`, `hiroshima`, `matsuyama`, `fukuoka`

---

### 放送中の番組情報

#### `get_live_programs() -> dict[str, LiveInfo]`

全チャンネルの放送中番組情報を取得します。キーはチャンネルID（`"r1"`, `"r2"`, `"fm"`）。

各 `LiveProgram` には `stream_url`（チャンネルのHLS URL）が自動注入されます。

```python
now = await client.get_live_programs()
for channel_id, info in now.items():
    program = info.present
    print(f"[{info.channel_name}] {program.title}")
    print(f"  シリーズ: {program.series_name}")
    print(f"  出演: {program.act}")
    print(f"  {program.start_at} 〜 {program.end_at}")
    print(f"  配信URL: {program.stream_url}")

# 前後の番組も取得可能
r1 = now["r1"]
if r1.previous:
    print(f"前の番組: {r1.previous.title}")
if r1.following:
    print(f"次の番組: {r1.following.title}")
```

#### `on_live_program_change(channel_id: str | None = None) -> AsyncGenerator[LiveInfo]`

番組が変わるたびに通知する async iterator です。停止するには `asyncio.Task.cancel()` を使います。

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `channel_id` | `str \| None` | `None` | 監視するチャンネル（`None` で全チャンネル） |

```python
# 全チャンネルを監視
async for info in client.on_live_program_change():
    print(f"番組が変わりました: [{info.channel_name}] {info.present.title}")

# 特定チャンネルのみ監視
async for info in client.on_live_program_change(channel_id="fm"):
    print(f"FM: {info.present.title}")
```

---

### 聞き逃し（オンデマンド）

#### `get_ondemand_new_arrivals(*, channel, filter_fn) -> list[OndemandSeries]`

聞き逃し新着番組を取得します。

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `channel` | `str \| None` | `None` | チャンネルで絞り込み（例: `"r1"`, `"fm"`） |
| `filter_fn` | `Callable \| None` | `None` | カスタムフィルタ関数 |

```python
# 新着番組の一覧
series_list = await client.get_ondemand_new_arrivals()
for s in series_list:
    print(f"{s.title} ({s.series_site_id})")

# チャンネルで絞り込み
fm_series = await client.get_ondemand_new_arrivals(channel="fm")
```

#### `search_ondemand(keyword: str) -> list[OndemandSeries]`

キーワードで聞き逃し番組を検索します。

```python
results = await client.search_ondemand("ゴンチチ")
for s in results:
    print(f"{s.title} ({s.radio_broadcast})")
```

#### `get_genres() -> list[Genre]`

オンデマンドのジャンル一覧を取得します。

```python
genres = await client.get_genres()
for g in genres:
    print(f"{g.genre}: {g.name}")
```

#### `get_ondemand_by_genre(genre: str) -> list[OndemandSeries]`

ジャンルで絞り込んだ番組一覧を取得します。

```python
music = await client.get_ondemand_by_genre("music")
```

#### `get_ondemand_by_kana(kana: Kana) -> list[OndemandSeries]`

五十音の頭文字で番組を絞り込みます。

```python
# "あ行" の番組
a_series = await client.get_ondemand_by_kana("a")
```

利用可能な値: `a`, `k`, `s`, `t`, `n`, `h`, `m`, `y`, `r`, `w`

#### `get_ondemand_by_date(onair_date: date) -> list[OndemandSeries]`

放送日で番組を取得します。

```python
from datetime import date

today = await client.get_ondemand_by_date(date(2026, 3, 10))
```

#### `get_ondemand_programs(series_site_id: str, corner_site_id: str) -> list[OndemandProgram]`

番組のエピソード一覧と再生URLを取得します。

```python
episodes = await client.get_ondemand_programs(
    series_site_id=series_list[0].series_site_id,
    corner_site_id=series_list[0].corner_site_id,
)
for ep in episodes:
    print(f"  {ep.title}: {ep.stream_url}")
    print(f"  {ep.start_at} 〜 {ep.end_at}")
    print(f"  配信終了: {ep.closed_at}")
```

---

### 設定の再読み込み

#### `refresh() -> None`

NHKは配信URLを不定期に変更します。長時間稼働するアプリケーションでは定期的に設定を再取得してください。初回は自動実行されます。

```python
await client.refresh()
```

---

### データモデル

#### `Program` (Protocol)

すべての番組モデルの共通インターフェイス。`LiveProgram`、`OndemandProgram`、`OndemandSeries` が実装します。

| フィールド | 型 | 説明 |
|---|---|---|
| `title` | `str` | 番組タイトル |
| `description` | `str` | 番組概要 |
| `thumbnail_url` | `str \| None` | サムネイルURL |
| `series_name` | `str` | シリーズ名 |
| `series_site_id` | `str` | シリーズサイトID |

```python
from nhk_radio import Program

def show_program(p: Program) -> None:
    print(f"{p.series_name}: {p.title}")

# ライブ番組でもオンデマンドでも同じように扱える
show_program(now["r1"].present)
show_program(episodes[0])
```

#### `RadioProgram`

再生可能な番組の基底クラス。`Program` を実装し、以下のフィールドを追加します。

| フィールド | 型 | 説明 |
|---|---|---|
| `act` | `str` | 出演者 |
| `channel_id` | `str` | チャンネルID |
| `stream_url` | `str` | HLS配信URL |
| `start_at` | `datetime` | 放送開始時刻 |
| `end_at` | `datetime` | 放送終了時刻 |

#### `LiveProgram` (extends `RadioProgram`)

ライブ放送中の番組。

| フィールド | 型 | 説明 |
|---|---|---|
| `event_id` | `str` | 放送イベントID |

#### `OndemandProgram` (extends `RadioProgram`)

聞き逃しエピソード。

| フィールド | 型 | 説明 |
|---|---|---|
| `episode_id` | `str` | エピソードID |
| `closed_at` | `datetime \| None` | 配信終了日時 |

#### `LiveInfo`

| フィールド | 型 | 説明 |
|---|---|---|
| `channel_id` | `str` | チャンネルID |
| `channel_name` | `str` | チャンネル名 |
| `previous` | `LiveProgram \| None` | 前の番組 |
| `present` | `LiveProgram` | 現在の番組 |
| `following` | `LiveProgram \| None` | 次の番組 |

#### `OndemandSeries`

聞き逃し番組のカタログエントリ。`Program` を実装。

| フィールド | 型 | 説明 |
|---|---|---|
| `title` | `str` | シリーズタイトル |
| `description` | `str` | 概要 |
| `thumbnail_url` | `str \| None` | サムネイルURL |
| `series_site_id` | `str` | シリーズサイトID |
| `series_name` | `str` | シリーズ名 |
| `radio_broadcast` | `str` | 放送チャンネル（例: `"R1"`, `"FM"`, `"R1,FM"`） |
| `corner_site_id` | `str` | コーナーサイトID |
| `corner_name` | `str` | コーナー名 |

#### `Genre`

| フィールド | 型 | 説明 |
|---|---|---|
| `genre` | `str` | ジャンルID |
| `name` | `str` | ジャンル名 |

#### `Kana`

五十音フィルタ用のリテラル型: `"a"`, `"k"`, `"s"`, `"t"`, `"n"`, `"h"`, `"m"`, `"y"`, `"r"`, `"w"`

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

---

### 例外

すべて `NhkRadioError` を継承しています。

| 例外 | 説明 | 属性 |
|---|---|---|
| `NhkRadioError` | 基底例外クラス | — |
| `ConfigFetchError` | config_web.xml の取得・パース失敗 | — |
| `AreaNotFoundError` | 指定した地域が存在しない | `area_id: str`, `available: list[str]` |
| `ApiError` | APIリクエスト失敗 | `status: int`, `url: str` |
| `NetworkError` | ネットワーク接続失敗 | `url: str` |

```python
from nhk_radio import NhkRadioError, ConfigFetchError, AreaNotFoundError

try:
    channels = await client.get_channels()
except ConfigFetchError:
    # config_web.xml の取得・パースに失敗
    pass
except AreaNotFoundError as e:
    # 指定した地域が存在しない
    print(f"利用可能: {e.available}")
except NhkRadioError:
    # その他のエラー
    pass
```

## Home Assistant での利用

このライブラリは Home Assistant Custom Integration から利用することを想定しています。

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
