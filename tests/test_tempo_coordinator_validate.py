"""Tests for TempoDataCoordinator._validate_and_cache_data and get_data."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from custom_components.tempo_rte_forecast.tempo_coordinator import TempoDataCoordinator
from tests.conftest import TODAY, TOMORROW

_DAY_CHANGE = "06:00:00"
_PATCH_DATE = patch(
    "custom_components.tempo_rte_forecast.tempo_coordinator.get_tempo_date",
    side_effect=lambda off, *_a, **_k: TODAY if off == 0 else TOMORROW,
)


def _make_coord() -> TempoDataCoordinator:
    coord = TempoDataCoordinator.__new__(TempoDataCoordinator)
    coord.tempo_day_change_time_str = _DAY_CHANGE
    coord.tempo_data = {}
    coord._cached_data = {}
    return coord


# ---------------------------------------------------------------------------
# _validate_and_cache_data
# ---------------------------------------------------------------------------


class TestValidateAndCacheData:
    def test_valid_j_and_j1_returns_true(self) -> None:
        coord = _make_coord()
        with _PATCH_DATE:
            result = coord._validate_and_cache_data({TODAY: "blue", TOMORROW: "white"})
        assert result is True

    def test_valid_data_updates_tempo_data(self) -> None:
        coord = _make_coord()
        with _PATCH_DATE:
            coord._validate_and_cache_data({TODAY: "blue", TOMORROW: "white"})
        assert coord.tempo_data[TODAY] == "blue"
        assert coord.tempo_data[TOMORROW] == "white"

    def test_valid_data_updates_cache(self) -> None:
        coord = _make_coord()
        with _PATCH_DATE:
            coord._validate_and_cache_data({TODAY: "red", TOMORROW: "blue", "2026-01-01": "white"})
        assert coord._cached_data["2026-01-01"] == "white"

    def test_empty_dict_returns_false(self) -> None:
        coord = _make_coord()
        with _PATCH_DATE:
            assert coord._validate_and_cache_data({}) is False

    def test_missing_today_returns_false(self) -> None:
        coord = _make_coord()
        with _PATCH_DATE:
            assert coord._validate_and_cache_data({TOMORROW: "blue"}) is False

    def test_invalid_color_today_returns_false(self) -> None:
        """Completely unknown color string fails validation."""
        coord = _make_coord()
        with _PATCH_DATE:
            assert coord._validate_and_cache_data({TODAY: "purple", TOMORROW: "blue"}) is False

    def test_missing_tomorrow_returns_false(self) -> None:
        coord = _make_coord()
        with _PATCH_DATE:
            assert coord._validate_and_cache_data({TODAY: "blue"}) is False

    def test_invalid_color_tomorrow_returns_false(self) -> None:
        coord = _make_coord()
        with _PATCH_DATE:
            assert coord._validate_and_cache_data({TODAY: "red", TOMORROW: "purple"}) is False

    def test_cache_updated_even_when_validation_fails(self) -> None:
        """Valid entries in the dict must be cached even if overall validation fails."""
        coord = _make_coord()
        with _PATCH_DATE:
            coord._validate_and_cache_data({TODAY: "blue", "2026-01-01": "red"})
        # TODAY is valid and goes into cache; validation still fails (no TOMORROW)
        assert coord._cached_data[TODAY] == "blue"
        assert coord._cached_data["2026-01-01"] == "red"

    def test_normalizes_to_lowercase(self) -> None:
        coord = _make_coord()
        with _PATCH_DATE:
            result = coord._validate_and_cache_data({TODAY: "Blue", TOMORROW: "WHITE"})
        assert result is True
        assert coord.tempo_data[TODAY] == "blue"
        assert coord.tempo_data[TOMORROW] == "white"

    def test_none_color_value_returns_false(self) -> None:
        coord = _make_coord()
        with _PATCH_DATE:
            assert coord._validate_and_cache_data({TODAY: None, TOMORROW: "blue"}) is False


# ---------------------------------------------------------------------------
# get_data
# ---------------------------------------------------------------------------


class TestGetData:
    def test_returns_from_tempo_data_first(self) -> None:
        coord = _make_coord()
        coord.tempo_data = {TODAY: "red"}
        coord._cached_data = {TODAY: "blue"}  # different value in cache
        assert coord.get_data(TODAY) == "red"

    def test_falls_back_to_cache_when_not_in_tempo_data(self) -> None:
        coord = _make_coord()
        coord.tempo_data = {}
        coord._cached_data = {TODAY: "white"}
        assert coord.get_data(TODAY) == "white"

    def test_returns_none_when_not_in_either(self) -> None:
        coord = _make_coord()
        assert coord.get_data("2020-01-01") is None
