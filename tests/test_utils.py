"""Tests for tempo_rte_forecast.utils."""

from __future__ import annotations

from datetime import date, datetime, time
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from custom_components.tempo_rte_forecast.utils import (
    get_color_code,
    get_color_emoji,
    get_color_name,
    get_color_name_en,
    get_icon_color,
    get_tempo_date,
    get_tempo_season,
    is_offpeak,
    normalize_color,
    normalize_contract,
    parse_offpeak_ranges,
)
from custom_components.tempo_rte_forecast.const import CONTRACT_TEMPO

PARIS = ZoneInfo("Europe/Paris")


def _paris_now(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, 0, tzinfo=PARIS)


class TestParseOffpeakRanges:
    def test_single_range(self) -> None:
        assert parse_offpeak_ranges("22:00-06:00") == [(time(22, 0), time(6, 0))]

    def test_multiple_ranges(self) -> None:
        assert parse_offpeak_ranges("22:00-06:00, 12:00-14:00") == [
            (time(22, 0), time(6, 0)),
            (time(12, 0), time(14, 0)),
        ]

    def test_empty_string(self) -> None:
        assert parse_offpeak_ranges("") == []

    def test_invalid_range_is_skipped(self) -> None:
        assert parse_offpeak_ranges("invalid,22:00-06:00") == [(time(22, 0), time(6, 0))]


class TestIsOffpeak:
    @pytest.fixture
    def night_range(self) -> list[tuple[time, time]]:
        return [(time(22, 0), time(6, 0))]

    def test_inside_offpeak_after_midnight(self, night_range: list[tuple[time, time]]) -> None:
        assert is_offpeak(_paris_now(2026, 6, 11, 2, 30), night_range) is True

    def test_inside_offpeak_before_midnight(self, night_range: list[tuple[time, time]]) -> None:
        assert is_offpeak(_paris_now(2026, 6, 11, 23, 0), night_range) is True

    def test_outside_offpeak(self, night_range: list[tuple[time, time]]) -> None:
        assert is_offpeak(_paris_now(2026, 6, 11, 12, 0), night_range) is False

    def test_daytime_range(self) -> None:
        ranges = [(time(12, 0), time(14, 0))]
        assert is_offpeak(_paris_now(2026, 6, 11, 13, 0), ranges) is True
        assert is_offpeak(_paris_now(2026, 6, 11, 15, 0), ranges) is False


class TestNormalizeContract:
    def test_legacy_values(self) -> None:
        assert normalize_contract("Tempo") == CONTRACT_TEMPO
        assert normalize_contract("Base") == "base"
        assert normalize_contract("Heures Creuses") == "heures_creuses"

    def test_slug_values(self) -> None:
        assert normalize_contract(CONTRACT_TEMPO) == CONTRACT_TEMPO


class TestGetTempoSeason:
    def test_before_august(self) -> None:
        assert get_tempo_season(date(2026, 3, 15)) == "2025-2026"

    def test_from_august(self) -> None:
        assert get_tempo_season(date(2026, 8, 1)) == "2026-2027"


class TestNormalizeColor:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Bleu", "blue"),
            ("blanc", "white"),
            ("ROUGE", "red"),
            ("blue", "blue"),
            (None, "unknown"),
            ("", "unknown"),
            ("purple", "purple"),
        ],
    )
    def test_normalize(self, raw: str | None, expected: str) -> None:
        assert normalize_color(raw) == expected


class TestColorHelpers:
    def test_color_metadata(self) -> None:
        assert get_color_code("bleu") == 1
        assert get_color_name("white") == "Blanc"
        assert get_color_name_en("rouge") == "red"
        assert get_color_emoji("blue") == "🔵"
        assert get_color_code(None) == 0


class TestGetIconColor:
    def test_defaults(self) -> None:
        assert get_icon_color({}, "blue") == "blue"
        assert get_icon_color({}, "unknown") == "yellow"

    def test_custom_options(self) -> None:
        options = {"icon_color_red": "orange"}
        assert get_icon_color(options, "red") == "orange"


class TestGetTempoDate:
    @patch("custom_components.tempo_rte_forecast.utils.dt_util.get_time_zone")
    @patch("custom_components.tempo_rte_forecast.utils.dt_util.now")
    def test_same_calendar_day_after_change(
        self, mock_now, mock_tz
    ) -> None:
        mock_tz.return_value = PARIS
        mock_now.return_value = _paris_now(2026, 6, 11, 10, 0)
        assert get_tempo_date(0, "06:00:00") == "2026-06-11"
        assert get_tempo_date(1, "06:00:00") == "2026-06-12"

    @patch("custom_components.tempo_rte_forecast.utils.dt_util.get_time_zone")
    @patch("custom_components.tempo_rte_forecast.utils.dt_util.now")
    def test_before_day_change_uses_previous_tempo_day(
        self, mock_now, mock_tz
    ) -> None:
        mock_tz.return_value = PARIS
        mock_now.return_value = _paris_now(2026, 6, 11, 4, 0)
        assert get_tempo_date(0, "06:00:00") == "2026-06-10"
        assert get_tempo_date(1, "06:00:00") == "2026-06-11"
