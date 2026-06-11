"""Tests for PriceSensor and SpecificPriceSensor property logic."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.tempo_rte_forecast.const import (
    CONTRACT_BASE,
    CONTRACT_HEURES_CREUSES,
    CONTRACT_TEMPO,
)
from custom_components.tempo_rte_forecast.prices_sensor import PriceSensor, SpecificPriceSensor

_TEMPO_PRICES = {
    "blue": {"HP": 0.1749, "HC": 0.1486},
    "white": {"HP": 0.3630, "HC": 0.1894},
    "red": {"HP": 0.7562, "HC": 0.2720},
}
_BASE_PRICES = {"HP": 0.2516}
_HC_PRICES = {"HP": 0.27, "HC": 0.2068}


def _mock_coord(data: dict) -> MagicMock:
    coord = MagicMock()
    coord.data = data
    return coord


def _mock_entry(options: dict | None = None) -> MagicMock:
    entry = MagicMock()
    entry.entry_id = "test"
    entry.options = options or {}
    return entry


def _make_price_sensor(coord_data: dict | None = None) -> PriceSensor:
    coord = _mock_coord(coord_data or {})
    entry = _mock_entry()
    sensor = PriceSensor.__new__(PriceSensor)
    sensor.coordinator = coord
    sensor.entry = entry
    return sensor


def _make_specific_sensor(
    coord_data: dict | None = None,
    key: str = "HP",
    color: str | None = None,
) -> SpecificPriceSensor:
    coord = _mock_coord(coord_data or {})
    entry = _mock_entry()
    sensor = SpecificPriceSensor.__new__(SpecificPriceSensor)
    sensor.coordinator = coord
    sensor.entry = entry
    sensor._key = key
    sensor._color = color.lower() if color else None
    return sensor


# ---------------------------------------------------------------------------
# PriceSensor
# ---------------------------------------------------------------------------


class TestPriceSensorNativeValue:
    def test_returns_price_from_data(self) -> None:
        sensor = _make_price_sensor({"price": 0.1749})
        assert sensor.native_value == pytest.approx(0.1749)

    def test_returns_none_when_no_data(self) -> None:
        sensor = _make_price_sensor(None)
        sensor.coordinator.data = None
        assert sensor.native_value is None

    def test_extra_attributes_contract_and_period(self) -> None:
        data = {
            "contract": CONTRACT_TEMPO,
            "is_hc": False,
            "is_hp": True,
            "current_period": "HP",
            "last_update": "2026-06-11T12:00:00",
            "prices_last_update": None,
            "tempo_color": "blue",
            "is_blue_hp": True,
            "is_blue_hc": False,
            "is_white_hp": False,
            "is_white_hc": False,
            "is_red_hp": False,
            "is_red_hc": False,
            "next_period_change": "22:00:00",
        }
        sensor = _make_price_sensor(data)
        attrs = sensor.extra_state_attributes
        assert attrs["contract"] == CONTRACT_TEMPO
        assert attrs["current_period"] == "HP"
        assert attrs["is_blue_hp"] is True
        assert attrs["is_red_hc"] is False
        assert "tempo_color" in attrs


# ---------------------------------------------------------------------------
# SpecificPriceSensor — native_value
# ---------------------------------------------------------------------------


class TestSpecificPriceSensorNativeValue:
    def test_tempo_blue_hp(self) -> None:
        data = {"contract_prices": _TEMPO_PRICES}
        sensor = _make_specific_sensor(data, key="HP", color="blue")
        assert sensor.native_value == pytest.approx(0.1749)

    def test_tempo_red_hc(self) -> None:
        data = {"contract_prices": _TEMPO_PRICES}
        sensor = _make_specific_sensor(data, key="HC", color="red")
        assert sensor.native_value == pytest.approx(0.2720)

    def test_base_hp_no_color(self) -> None:
        data = {"contract_prices": _BASE_PRICES}
        sensor = _make_specific_sensor(data, key="HP", color=None)
        assert sensor.native_value == pytest.approx(0.2516)

    def test_hc_contract_hc_period(self) -> None:
        data = {"contract_prices": _HC_PRICES}
        sensor = _make_specific_sensor(data, key="HC", color=None)
        assert sensor.native_value == pytest.approx(0.2068)

    def test_returns_none_when_no_data(self) -> None:
        sensor = _make_specific_sensor(None, key="HP", color="blue")
        sensor.coordinator.data = None
        assert sensor.native_value is None

    def test_returns_none_when_color_not_in_prices(self) -> None:
        data = {"contract_prices": {}}
        sensor = _make_specific_sensor(data, key="HP", color="blue")
        assert sensor.native_value is None


# ---------------------------------------------------------------------------
# SpecificPriceSensor — active attribute
# ---------------------------------------------------------------------------


class TestSpecificPriceSensorActive:
    def test_tempo_active_when_color_and_period_match(self) -> None:
        data = {
            "contract_prices": _TEMPO_PRICES,
            "contract": CONTRACT_TEMPO,
            "tempo_color": "blue",
            "current_period": "HP",
            "subscribed_power": "9",
        }
        sensor = _make_specific_sensor(data, key="HP", color="blue")
        attrs = sensor.extra_state_attributes
        assert attrs["active"] is True

    def test_tempo_inactive_when_period_differs(self) -> None:
        data = {
            "contract_prices": _TEMPO_PRICES,
            "contract": CONTRACT_TEMPO,
            "tempo_color": "blue",
            "current_period": "HC",  # sensor is HP
            "subscribed_power": "9",
        }
        sensor = _make_specific_sensor(data, key="HP", color="blue")
        attrs = sensor.extra_state_attributes
        assert attrs["active"] is False

    def test_tempo_inactive_when_color_differs(self) -> None:
        data = {
            "contract_prices": _TEMPO_PRICES,
            "contract": CONTRACT_TEMPO,
            "tempo_color": "red",   # sensor is "blue"
            "current_period": "HP",
            "subscribed_power": "9",
        }
        sensor = _make_specific_sensor(data, key="HP", color="blue")
        attrs = sensor.extra_state_attributes
        assert attrs["active"] is False

    def test_base_contract_always_active(self) -> None:
        data = {
            "contract_prices": _BASE_PRICES,
            "contract": CONTRACT_BASE,
            "tempo_color": None,
            "current_period": "HP",
            "subscribed_power": "9",
        }
        sensor = _make_specific_sensor(data, key="HP", color=None)
        attrs = sensor.extra_state_attributes
        assert attrs["active"] is True

    def test_hc_hp_sensor_active_when_in_hp_period(self) -> None:
        data = {
            "contract_prices": _HC_PRICES,
            "contract": CONTRACT_HEURES_CREUSES,
            "tempo_color": None,
            "current_period": "HP",
            "subscribed_power": "9",
        }
        sensor = _make_specific_sensor(data, key="HP", color=None)
        attrs = sensor.extra_state_attributes
        assert attrs["active"] is True

    def test_hc_hc_sensor_inactive_when_in_hp_period(self) -> None:
        data = {
            "contract_prices": _HC_PRICES,
            "contract": CONTRACT_HEURES_CREUSES,
            "tempo_color": None,
            "current_period": "HP",
            "subscribed_power": "9",
        }
        sensor = _make_specific_sensor(data, key="HC", color=None)
        attrs = sensor.extra_state_attributes
        assert attrs["active"] is False
