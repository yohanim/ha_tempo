"""Tests for PriceCoordinator CSV parsing and price fetch."""

from __future__ import annotations

import io
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import aioresponses
import pytest

from custom_components.tempo_rte_forecast.const import PRICE_TEMPO_URL
from custom_components.tempo_rte_forecast.prices_coordinator import PriceCoordinator
from custom_components.tempo_rte_forecast.tempo_coordinator import TempoDataCoordinator
from tests.conftest import TODAY

PARIS = ZoneInfo("Europe/Paris")


TEMPO_CSV = """\
P_SOUSCRITE;DATE_DEBUT;DATE_FIN;PART_VARIABLE_HCBleu_TTC;PART_VARIABLE_HPBleu_TTC;PART_VARIABLE_HCBlanc_TTC;PART_VARIABLE_HPBlanc_TTC;PART_VARIABLE_HCRouge_TTC;PART_VARIABLE_HPRouge_TTC
9;2020-01-01;;0.1486;0.1749;0.1894;0.3630;0.2720;0.7562
6;2020-01-01;;0.1400;0.1600;0.1800;0.3500;0.2600;0.7400
"""

BASE_CSV = """\
P_SOUSCRITE;DATE_DEBUT;DATE_FIN;PART_VARIABLE_TTC
9;2020-01-01;;0.2516
"""


def test_parse_tempo_prices() -> None:
    """Tempo CSV rows are parsed for the subscribed power."""
    coordinator = PriceCoordinator.__new__(PriceCoordinator)
    coordinator._subscribed_power = "9"
    with patch(
        "custom_components.tempo_rte_forecast.prices_coordinator.dt_util.now"
    ) as mock_now:
        mock_now.return_value = datetime(2026, 6, 11, 12, 0, tzinfo=PARIS)
        prices = coordinator._parse_tempo_prices(io.StringIO(TEMPO_CSV))

    assert prices["blue"]["HP"] == pytest.approx(0.1749)
    assert prices["red"]["HC"] == pytest.approx(0.2720)


def test_parse_base_prices() -> None:
    """Base contract CSV parsing."""
    coordinator = PriceCoordinator.__new__(PriceCoordinator)
    coordinator._subscribed_power = "9"
    with patch(
        "custom_components.tempo_rte_forecast.prices_coordinator.dt_util.now"
    ) as mock_now:
        mock_now.return_value = datetime(2026, 6, 11, 12, 0, tzinfo=PARIS)
        prices = coordinator._parse_base_prices(io.StringIO(BASE_CSV))

    assert prices == {"HP": pytest.approx(0.2516)}


@pytest.mark.asyncio
async def test_fetch_and_parse_csv_from_url(hass, mock_config_entry) -> None:
    """CSV download via aiohttp is parsed end-to-end."""
    tempo = TempoDataCoordinator(hass, mock_config_entry)
    coordinator = PriceCoordinator(hass, mock_config_entry, tempo)
    coordinator._contract = "Tempo"
    coordinator._subscribed_power = "9"
    try:
        with aioresponses.aioresponses() as mocked:
            mocked.get(PRICE_TEMPO_URL, body=TEMPO_CSV)
            with patch(
                "custom_components.tempo_rte_forecast.prices_coordinator.dt_util.now"
            ) as mock_now:
                mock_now.return_value = datetime(2026, 6, 11, 12, 0, tzinfo=PARIS)
                prices = await coordinator._fetch_and_parse_csv(
                    PRICE_TEMPO_URL, coordinator._parse_tempo_prices
                )
    finally:
        await coordinator.async_shutdown()
        await tempo.async_shutdown()

    assert prices["white"]["HP"] == pytest.approx(0.3630)


@pytest.mark.asyncio
async def test_async_update_data_uses_tempo_color(
    hass, mock_config_entry, fixed_tempo_dates
) -> None:
    """Current price reflects Tempo color from the tempo coordinator."""
    tempo = TempoDataCoordinator(hass, mock_config_entry)
    tempo.tempo_data = {TODAY: "red"}
    tempo._cached_data = {TODAY: "red"}
    coordinator = PriceCoordinator(hass, mock_config_entry, tempo)
    coordinator._contract = "Tempo"
    coordinator._prices = {
        "Tempo": {
            "red": {"HP": 0.7562, "HC": 0.2720},
            "blue": {"HP": 0.1749, "HC": 0.1486},
            "white": {"HP": 0.3630, "HC": 0.1894},
        }
    }
    try:
        with patch(
            "custom_components.tempo_rte_forecast.prices_coordinator.is_offpeak",
            return_value=False,
        ):
            data = await coordinator._async_update_data()
    finally:
        await coordinator.async_shutdown()
        await tempo.async_shutdown()

    assert data["tempo_color"] == "red"
    assert data["price"] == pytest.approx(0.7562)
    assert data["is_red_hp"] is True
