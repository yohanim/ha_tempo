"""Tests for ForecastCoordinator._format_all_dates (date/probability formatting)."""

from __future__ import annotations

from custom_components.tempo_rte_forecast.forecast_coordinator import (
    ForecastCoordinator,
    _format_all_dates,
)
from custom_components.tempo_rte_forecast.const import OPENDPE_SERVICE_LIGHT, OPENDPE_SERVICE_FULL
from custom_components.tempo_rte_forecast.sensor_types import ForecastSensor


def _make_coord(service_type: str = OPENDPE_SERVICE_LIGHT) -> ForecastCoordinator:
    coord = ForecastCoordinator.__new__(ForecastCoordinator)
    coord.service_type = service_type
    coord._cached_data = {}
    return coord


# ---------------------------------------------------------------------------
# Light service — uses "couleur" key
# ---------------------------------------------------------------------------


def test_format_confirmed_day_light_service() -> None:
    """probability=1 means confirmed color; probability field stays as int 100."""
    coord = _make_coord(OPENDPE_SERVICE_LIGHT)
    data = [{"date": "2026-06-12", "couleur": "bleu", "probability": 1}]
    result = _format_all_dates(coord, data, "fr")
    assert "2026-06-12" in result
    sensor = result["2026-06-12"]
    assert isinstance(sensor, ForecastSensor)
    assert sensor.color == "bleu"
    assert sensor.probability == 100


def test_format_day_populates_cache() -> None:
    """Formatted sensors are stored in _cached_data."""
    coord = _make_coord()
    data = [{"date": "2026-06-12", "couleur": "blanc", "probability": 1}]
    _format_all_dates(coord, data, "en")
    assert "2026-06-12" in coord._cached_data


def test_format_multiple_days() -> None:
    coord = _make_coord()
    data = [
        {"date": "2026-06-12", "couleur": "bleu", "probability": 1},
        {"date": "2026-06-13", "couleur": "rouge", "probability": 1},
    ]
    result = _format_all_dates(coord, data, "en")
    assert len(result) == 2
    assert result["2026-06-13"].color == "rouge"


def test_format_day_with_probability_breakdown_builds_emoji_color() -> None:
    """When probability < 1 and individual probs given, color becomes an emoji string."""
    coord = _make_coord()
    data = [
        {
            "date": "2026-06-15",
            "couleur": "bleu",
            "probability": 0.6,
            "probability_bleu": 0.6,
            "probability_blanc": 0.3,
            "probability_rouge": 0.1,
        }
    ]
    result = _format_all_dates(coord, data, "fr")
    sensor = result["2026-06-15"]
    # color should be emojis sorted by probability (highest first)
    assert "🔵" in sensor.color
    assert "⚪" in sensor.color
    assert "🔴" in sensor.color


def test_format_day_probability_string_contains_percentages() -> None:
    """The probability attribute becomes space-separated percentage strings."""
    coord = _make_coord()
    data = [
        {
            "date": "2026-06-15",
            "couleur": "bleu",
            "probability": 0.6,
            "probability_bleu": 0.6,
            "probability_blanc": 0.4,
            "probability_rouge": 0.0,
        }
    ]
    result = _format_all_dates(coord, data, "fr")
    sensor = result["2026-06-15"]
    assert "60" in str(sensor.probability)
    assert "40" in str(sensor.probability)


def test_format_invalid_row_skipped() -> None:
    """A row with a bad date must not crash — it is silently skipped."""
    coord = _make_coord()
    data = [
        {"date": "not-a-date", "couleur": "bleu", "probability": 1},
        {"date": "2026-06-12", "couleur": "blanc", "probability": 1},
    ]
    result = _format_all_dates(coord, data, "en")
    assert "2026-06-12" in result
    assert "not-a-date" not in result


# ---------------------------------------------------------------------------
# Full service — uses "tempo_color" key
# ---------------------------------------------------------------------------


def test_format_full_service_uses_tempo_color_key() -> None:
    """Full service reads "tempo_color" instead of "couleur"."""
    coord = _make_coord(OPENDPE_SERVICE_FULL)
    data = [{"date": "2026-06-12", "tempo_color": "rouge", "couleur": "bleu", "probability": 1}]
    result = _format_all_dates(coord, data, "en")
    assert result["2026-06-12"].color == "rouge"


def test_format_locale_fr_short_date() -> None:
    """French locale produces a non-empty short_date and day strings."""
    coord = _make_coord()
    data = [{"date": "2026-06-12", "couleur": "bleu", "probability": 1}]
    result = _format_all_dates(coord, data, "fr")
    sensor = result["2026-06-12"]
    assert sensor.short_date != ""
    assert sensor.day != ""
