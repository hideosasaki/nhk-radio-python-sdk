"""Tests for model Protocol conformance."""

from nhk_radio.models import NowOnAirProgram, OndemandEpisode, Program


def test_now_on_air_program_is_program() -> None:
    program = NowOnAirProgram(
        event_id="r1-130-123",
        channel_id="r1",
        title="Test Program",
        description="A test",
        series_name="Test Series",
        act="Host Name",
        start_at="2026-03-09T20:00:00+09:00",
        end_at="2026-03-09T21:00:00+09:00",
        thumbnail_url="https://example.com/logo.png",
    )
    assert isinstance(program, Program)
    assert program.title == "Test Program"
    assert program.description == "A test"
    assert program.thumbnail_url == "https://example.com/logo.png"
    assert program.series_name == "Test Series"
    assert program.act == "Host Name"


def test_ondemand_episode_is_program() -> None:
    episode = OndemandEpisode(
        episode_id="123",
        title="Test Episode",
        description="A test episode",
        stream_url="https://example.com/stream.m3u8",
        onair_date="3月9日(月)午後5:00放送",
        closed_at="2026年3月16日(月)午後6:00配信終了",
        thumbnail_url="https://example.com/thumb.png",
        series_name="Test Series",
        act="Guest Name",
    )
    assert isinstance(episode, Program)
    assert episode.title == "Test Episode"
    assert episode.description == "A test episode"
    assert episode.thumbnail_url == "https://example.com/thumb.png"
    assert episode.series_name == "Test Series"
    assert episode.act == "Guest Name"
