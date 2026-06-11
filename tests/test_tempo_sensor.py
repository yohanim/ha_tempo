"""Tests for TempoSensor and TempoNextDayCombinedSensor property logic."""

from __future__ import annotations

import logging
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from custom_components.tempo_rte_forecast.sensor_types import ForecastSensor
from custom_components.tempo_rte_forecast.tempo_sensor import (
    TempoNextDayCombinedSensor,
    TempoSensor,
)

TODAY = "2026-06-11"
TOMORROW = "2026-06-12"

_PATCH_DATE = "custom_components.tempo_rte_forecast.tempo_sensor.get_tempo_date"


def _mock_coord(rte_data: dict | None = None, options: dict | None = None) -> MagicMock:
    coord = MagicMock()
    coord.entry.entry_id = "test"
    coord.entry.options = options or {}
    data = rte_data or {}
    coord.tempo_data = data
    coord.get_data = MagicMock(side_effect=lambda d: data.get(d))
    return coord


def _mock_fc(forecast_data: dict | None = None) -> MagicMock:
    fc = MagicMock()
    data = forecast_data or {}
    fc.get_data = MagicMock(side_effect=lambda d: data.get(d))
    return fc


def _make_sensor(
    index: int = 0,
    rte_data: dict | None = None,
    forecast_data: dict | None = None,
    options: dict | None = None,
) -> TempoSensor:
    coord = _mock_coord(rte_data, options)
    sensor = TempoSensor.__new__(TempoSensor)
    sensor.coordinator = coord
    sensor.index = index
    sensor.tempo_day_change_time_str = "06:00:00"
    sensor._last_state = None
    sensor._forecast_coordinator = _mock_fc(forecast_data) if forecast_data is not None else None
    return sensor


def _make_combined_sensor(
    rte_data: dict | None = None,
    forecast_data: dict | None = None,
    options: dict | None = None,
) -> TempoNextDayCombinedSensor:
    coord = _mock_coord(rte_data, options)
    fc = _mock_fc(forecast_data)
    sensor = TempoNextDayCombinedSensor.__new__(TempoNextDayCombinedSensor)
    sensor.coordinator = coord
    sensor.forecast_coordinator = fc
    sensor.tempo_day_change_time_str = "06:00:00"
    return sensor


def _fs(color: str, day: str = TODAY) -> ForecastSensor:
    return ForecastSensor(
        date=date.fromisoformat(day),
        short_date="11/06",
        day="jeu.",
        color=color,
        probability=100,
    )


# ---------------------------------------------------------------------------
# TempoSensor._effective_color_raw
# ---------------------------------------------------------------------------


class TestEffectiveColorRaw:
    def test_rte_color_wins(self) -> None:
        sensor = _make_sensor(0, rte_data={TODAY: "blue"}, forecast_data={TODAY: _fs("white")})
        with patch(_PATCH_DATE, side_effect=lambda off, *a, **k: TODAY if off == 0 else TOMORROW):
            assert sensor._effective_color_raw() == "blue"

    def test_falls_back_to_opendpe_when_rte_none(self) -> None:
        sensor = _make_sensor(0, rte_data={}, forecast_data={TODAY: _fs("white")})
        with patch(_PATCH_DATE, side_effect=lambda off, *a, **k: TODAY if off == 0 else TOMORROW):
            assert sensor._effective_color_raw() == "white"

    def test_returns_none_when_rte_none_and_no_fc(self) -> None:
        sensor = _make_sensor(0, rte_data={})
        with patch(_PATCH_DATE, side_effect=lambda off, *a, **k: TODAY if off == 0 else TOMORROW):
            assert sensor._effective_color_raw() is None

    def test_returns_none_when_both_sources_empty(self) -> None:
        sensor = _make_sensor(0, rte_data={}, forecast_data={})
        with patch(_PATCH_DATE, side_effect=lambda off, *a, **k: TODAY if off == 0 else TOMORROW):
            assert sensor._effective_color_raw() is None

    def test_uses_index_offset_for_tomorrow(self) -> None:
        sensor = _make_sensor(1, rte_data={TOMORROW: "red"})
        with patch(_PATCH_DATE, side_effect=lambda off, *a, **k: TODAY if off == 0 else TOMORROW):
            assert sensor._effective_color_raw() == "red"


# ---------------------------------------------------------------------------
# TempoSensor.native_value
# ---------------------------------------------------------------------------


class TestTempoSensorNativeValue:
    def test_blue(self) -> None:
        sensor = _make_sensor(0, rte_data={TODAY: "blue"})
        with patch(_PATCH_DATE, return_value=TODAY):
            assert sensor.native_value == "blue"

    def test_none_returns_unknown(self) -> None:
        sensor = _make_sensor(0, rte_data={})
        with patch(_PATCH_DATE, return_value=TODAY):
            assert sensor.native_value == "unknown"

    def test_opendpe_fallback_normalized(self) -> None:
        sensor = _make_sensor(0, rte_data={}, forecast_data={TODAY: _fs("blanc")})
        with patch(_PATCH_DATE, return_value=TODAY):
            assert sensor.native_value == "white"

    def test_available_is_always_true(self) -> None:
        sensor = _make_sensor(0, rte_data={})
        assert sensor.available is True


# ---------------------------------------------------------------------------
# TempoSensor.extra_state_attributes
# ---------------------------------------------------------------------------


class TestTempoSensorAttributes:
    def test_data_source_api_when_in_tempo_data(self) -> None:
        coord = _mock_coord({TODAY: "blue"})
        sensor = TempoSensor.__new__(TempoSensor)
        sensor.coordinator = coord
        sensor.index = 0
        sensor.tempo_day_change_time_str = "06:00:00"
        sensor._last_state = None
        sensor._forecast_coordinator = None
        with patch(_PATCH_DATE, return_value=TODAY):
            attrs = sensor.extra_state_attributes
        assert attrs["data_source"] == "api"

    def test_data_source_cache_when_not_in_tempo_data(self) -> None:
        coord = _mock_coord()
        coord.tempo_data = {}               # NOT in tempo_data
        coord.get_data = MagicMock(return_value="red")  # but in cached_data
        sensor = TempoSensor.__new__(TempoSensor)
        sensor.coordinator = coord
        sensor.index = 0
        sensor.tempo_day_change_time_str = "06:00:00"
        sensor._last_state = None
        sensor._forecast_coordinator = None
        with patch(_PATCH_DATE, return_value=TODAY):
            attrs = sensor.extra_state_attributes
        assert attrs["data_source"] == "cache"

    def test_data_source_opendpe_when_rte_none(self) -> None:
        sensor = _make_sensor(0, rte_data={}, forecast_data={TODAY: _fs("white")})
        with patch(_PATCH_DATE, return_value=TODAY):
            attrs = sensor.extra_state_attributes
        assert attrs["data_source"] == "opendpe"

    def test_data_source_none_when_all_missing(self) -> None:
        sensor = _make_sensor(0, rte_data={}, forecast_data={})
        with patch(_PATCH_DATE, return_value=TODAY):
            attrs = sensor.extra_state_attributes
        assert attrs["data_source"] == "none"

    def test_j_sensor_has_no_tomorrow_attrs(self) -> None:
        sensor = _make_sensor(0, rte_data={TODAY: "blue"})
        with patch(_PATCH_DATE, return_value=TODAY):
            attrs = sensor.extra_state_attributes
        assert "tomorrow_is_blue" not in attrs

    def test_j1_sensor_has_tomorrow_attrs(self) -> None:
        sensor = _make_sensor(1, rte_data={TOMORROW: "red"})
        with patch(_PATCH_DATE, return_value=TOMORROW):
            attrs = sensor.extra_state_attributes
        assert "tomorrow_is_red" in attrs
        assert attrs["tomorrow_is_red"] is True
        assert attrs["tomorrow_is_blue"] is False

    def test_boolean_flags_correct_for_white(self) -> None:
        sensor = _make_sensor(0, rte_data={TODAY: "white"})
        with patch(_PATCH_DATE, return_value=TODAY):
            attrs = sensor.extra_state_attributes
        assert attrs["is_white"] is True
        assert attrs["is_blue"] is False
        assert attrs["is_red"] is False


# ---------------------------------------------------------------------------
# TempoSensor._handle_coordinator_update (state-change logging)
# ---------------------------------------------------------------------------


class TestHandleCoordinatorUpdate:
    def test_last_state_updated_on_call(self) -> None:
        sensor = _make_sensor(0, rte_data={TODAY: "blue"})
        sensor.async_write_ha_state = MagicMock()
        with patch(_PATCH_DATE, return_value=TODAY):
            sensor._handle_coordinator_update()
        assert sensor._last_state == "blue"

    def test_state_change_is_logged(self, caplog) -> None:
        sensor = _make_sensor(0, rte_data={TODAY: "red"})
        sensor.async_write_ha_state = MagicMock()
        sensor._last_state = "blue"
        with patch(_PATCH_DATE, return_value=TODAY):
            with caplog.at_level(logging.INFO, logger="custom_components.tempo_rte_forecast.tempo_sensor"):
                sensor._handle_coordinator_update()
        assert "State change" in caplog.text
        assert "blue" in caplog.text
        assert "red" in caplog.text

    def test_no_log_when_state_unchanged(self, caplog) -> None:
        sensor = _make_sensor(0, rte_data={TODAY: "blue"})
        sensor.async_write_ha_state = MagicMock()
        sensor._last_state = "blue"
        with patch(_PATCH_DATE, return_value=TODAY):
            with caplog.at_level(logging.INFO, logger="custom_components.tempo_rte_forecast.tempo_sensor"):
                sensor._handle_coordinator_update()
        assert "State change" not in caplog.text

    def test_no_log_on_first_call_when_last_state_is_none(self, caplog) -> None:
        sensor = _make_sensor(0, rte_data={TODAY: "blue"})
        sensor.async_write_ha_state = MagicMock()
        sensor._last_state = None  # first call
        with patch(_PATCH_DATE, return_value=TODAY):
            with caplog.at_level(logging.INFO, logger="custom_components.tempo_rte_forecast.tempo_sensor"):
                sensor._handle_coordinator_update()
        assert "State change" not in caplog.text


# ---------------------------------------------------------------------------
# TempoNextDayCombinedSensor
# ---------------------------------------------------------------------------


class TestTempoNextDayCombinedSensor:
    def test_native_value_rte_known(self) -> None:
        sensor = _make_combined_sensor(rte_data={TOMORROW: "blue"})
        with patch(_PATCH_DATE, return_value=TOMORROW):
            assert sensor.native_value == "blue"

    def test_native_value_rte_unknown_opendpe_known(self) -> None:
        sensor = _make_combined_sensor(rte_data={}, forecast_data={TOMORROW: _fs("white", TOMORROW)})
        with patch(_PATCH_DATE, return_value=TOMORROW):
            value = sensor.native_value
        # Returns an emoji composite string (intentional design)
        assert "⚪" in value
        assert "❓" in value

    def test_native_value_both_unknown(self) -> None:
        sensor = _make_combined_sensor(rte_data={}, forecast_data={})
        with patch(_PATCH_DATE, return_value=TOMORROW):
            assert sensor.native_value == "unknown"

    def test_available_true_when_rte_has_data(self) -> None:
        sensor = _make_combined_sensor(rte_data={TOMORROW: "red"}, forecast_data={})
        with patch(_PATCH_DATE, return_value=TOMORROW):
            assert sensor.available is True

    def test_available_true_when_only_opendpe(self) -> None:
        sensor = _make_combined_sensor(rte_data={}, forecast_data={TOMORROW: _fs("blue", TOMORROW)})
        with patch(_PATCH_DATE, return_value=TOMORROW):
            assert sensor.available is True

    def test_available_false_when_both_none(self) -> None:
        sensor = _make_combined_sensor(rte_data={}, forecast_data={})
        with patch(_PATCH_DATE, return_value=TOMORROW):
            assert sensor.available is False

    def test_extra_attributes_active_source_rte(self) -> None:
        sensor = _make_combined_sensor(
            rte_data={TOMORROW: "red"},
            forecast_data={TOMORROW: _fs("blue", TOMORROW)},
        )
        with patch(_PATCH_DATE, return_value=TOMORROW):
            attrs = sensor.extra_state_attributes
        assert attrs["active_source"] == "RTE"
        assert attrs["tomorrow_is_red"] is True
        assert attrs["tomorrow_is_blue"] is False

    def test_extra_attributes_active_source_opendpe(self) -> None:
        sensor = _make_combined_sensor(
            rte_data={},
            forecast_data={TOMORROW: _fs("white", TOMORROW)},
        )
        with patch(_PATCH_DATE, return_value=TOMORROW):
            attrs = sensor.extra_state_attributes
        assert attrs["active_source"] == "OpenDPE"
        assert attrs["tomorrow_is_white"] is True
