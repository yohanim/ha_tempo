"""Tests for PriceCoordinator CSV parsing and price fetch."""

from __future__ import annotations

import io
from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.tempo_rte_forecast.const import (
    CONTRACT_BASE,
    CONTRACT_HEURES_CREUSES,
    CONTRACT_TEMPO,
    PRICE_TEMPO_URL,
)
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

HPHC_CSV = """\
P_SOUSCRITE;DATE_DEBUT;DATE_FIN;PART_VARIABLE_HP_TTC;PART_VARIABLE_HC_TTC
9;2020-01-01;;0.27;0.2068
6;2020-01-01;;0.25;0.19
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
    coordinator._contract = CONTRACT_TEMPO
    coordinator._subscribed_power = "9"

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.read = AsyncMock(return_value=TEMPO_CSV.encode("utf-8"))
    coordinator.session = MagicMock()
    coordinator.session.get = AsyncMock(return_value=mock_resp)

    try:
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
    coordinator._contract = CONTRACT_TEMPO
    coordinator._prices = {
        CONTRACT_TEMPO: {
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


@pytest.mark.asyncio
async def test_async_force_prices_update_calls_update_prices(
    hass, mock_config_entry
) -> None:
    """async_force_prices_update must delegate to _update_prices(force=True)."""
    from unittest.mock import AsyncMock, patch

    tempo = TempoDataCoordinator(hass, mock_config_entry)
    coordinator = PriceCoordinator(hass, mock_config_entry, tempo)
    try:
        with patch.object(
            coordinator, "_update_prices", new_callable=AsyncMock
        ) as mock_update:
            await coordinator.async_force_prices_update()
            mock_update.assert_awaited_once_with(force=True)
    finally:
        await coordinator.async_shutdown()
        await tempo.async_shutdown()


# ---------------------------------------------------------------------------
# _parse_hphc_prices
# ---------------------------------------------------------------------------


def test_parse_hphc_prices() -> None:
    """HP/HC CSV rows are parsed for the subscribed power."""
    coordinator = PriceCoordinator.__new__(PriceCoordinator)
    coordinator._subscribed_power = "9"
    with patch(
        "custom_components.tempo_rte_forecast.prices_coordinator.dt_util.now"
    ) as mock_now:
        mock_now.return_value = datetime(2026, 6, 11, 12, 0, tzinfo=PARIS)
        prices = coordinator._parse_hphc_prices(io.StringIO(HPHC_CSV))

    assert prices["HP"] == pytest.approx(0.27)
    assert prices["HC"] == pytest.approx(0.2068)


def test_parse_hphc_prices_wrong_power() -> None:
    """If subscribed power doesn't match, returns empty dict."""
    coordinator = PriceCoordinator.__new__(PriceCoordinator)
    coordinator._subscribed_power = "3"  # not in CSV
    with patch(
        "custom_components.tempo_rte_forecast.prices_coordinator.dt_util.now"
    ) as mock_now:
        mock_now.return_value = datetime(2026, 6, 11, 12, 0, tzinfo=PARIS)
        prices = coordinator._parse_hphc_prices(io.StringIO(HPHC_CSV))

    assert prices == {}


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------


def test_parse_date_iso_format() -> None:
    """YYYY-MM-DD ISO format is parsed correctly."""
    coord = PriceCoordinator.__new__(PriceCoordinator)
    assert coord._parse_date("2026-06-11") == date(2026, 6, 11)


def test_parse_date_french_format() -> None:
    """DD/MM/YYYY French format is parsed correctly."""
    coord = PriceCoordinator.__new__(PriceCoordinator)
    assert coord._parse_date("11/06/2026") == date(2026, 6, 11)


def test_parse_date_empty_returns_none() -> None:
    coord = PriceCoordinator.__new__(PriceCoordinator)
    assert coord._parse_date("") is None
    assert coord._parse_date(None) is None


def test_parse_date_invalid_returns_none() -> None:
    coord = PriceCoordinator.__new__(PriceCoordinator)
    assert coord._parse_date("not-a-date") is None


# ---------------------------------------------------------------------------
# _is_row_active
# ---------------------------------------------------------------------------


def test_is_row_active_no_end_date() -> None:
    """Row with no end date is active as long as start <= target."""
    coord = PriceCoordinator.__new__(PriceCoordinator)
    row = {"DATE_DEBUT": "2020-01-01", "DATE_FIN": ""}
    assert coord._is_row_active(row, date(2026, 6, 11)) is True


def test_is_row_active_within_range() -> None:
    coord = PriceCoordinator.__new__(PriceCoordinator)
    row = {"DATE_DEBUT": "2020-01-01", "DATE_FIN": "2030-12-31"}
    assert coord._is_row_active(row, date(2026, 6, 11)) is True


def test_is_row_active_before_start() -> None:
    coord = PriceCoordinator.__new__(PriceCoordinator)
    row = {"DATE_DEBUT": "2027-01-01", "DATE_FIN": ""}
    assert coord._is_row_active(row, date(2026, 6, 11)) is False


def test_is_row_active_after_end() -> None:
    coord = PriceCoordinator.__new__(PriceCoordinator)
    row = {"DATE_DEBUT": "2020-01-01", "DATE_FIN": "2025-12-31"}
    assert coord._is_row_active(row, date(2026, 6, 11)) is False


def test_is_row_active_on_start_boundary() -> None:
    coord = PriceCoordinator.__new__(PriceCoordinator)
    row = {"DATE_DEBUT": "2026-06-11", "DATE_FIN": ""}
    assert coord._is_row_active(row, date(2026, 6, 11)) is True


def test_is_row_active_on_end_boundary() -> None:
    coord = PriceCoordinator.__new__(PriceCoordinator)
    row = {"DATE_DEBUT": "2020-01-01", "DATE_FIN": "2026-06-11"}
    assert coord._is_row_active(row, date(2026, 6, 11)) is True


def test_is_row_active_missing_start_returns_false() -> None:
    coord = PriceCoordinator.__new__(PriceCoordinator)
    row = {"DATE_DEBUT": "", "DATE_FIN": ""}
    assert coord._is_row_active(row, date(2026, 6, 11)) is False


# ---------------------------------------------------------------------------
# _async_update_data — base and HC contracts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_update_data_base_contract(
    hass, mock_config_entry, fixed_tempo_dates
) -> None:
    """Base contract: price = HP price, period is always HP."""
    tempo = TempoDataCoordinator(hass, mock_config_entry)
    coordinator = PriceCoordinator(hass, mock_config_entry, tempo)
    coordinator._contract = CONTRACT_BASE
    coordinator._prices = {
        CONTRACT_BASE: {"HP": 0.2516},
    }
    coordinator._offpeak_ranges = []
    try:
        data = await coordinator._async_update_data()
    finally:
        await coordinator.async_shutdown()
        await tempo.async_shutdown()

    assert data["contract"] == CONTRACT_BASE
    assert data["price"] == pytest.approx(0.2516)
    assert data["current_period"] == "HP"
    assert data["is_hc"] is False
    assert data["tempo_color"] is None


@pytest.mark.asyncio
async def test_async_update_data_hc_contract(
    hass, mock_config_entry, fixed_tempo_dates
) -> None:
    """HC contract: price follows is_offpeak() result."""
    tempo = TempoDataCoordinator(hass, mock_config_entry)
    coordinator = PriceCoordinator(hass, mock_config_entry, tempo)
    coordinator._contract = CONTRACT_HEURES_CREUSES
    coordinator._prices = {
        CONTRACT_HEURES_CREUSES: {"HP": 0.27, "HC": 0.2068},
    }
    coordinator._offpeak_ranges = []
    try:
        with patch(
            "custom_components.tempo_rte_forecast.prices_coordinator.is_offpeak",
            return_value=True,  # currently in off-peak
        ):
            data = await coordinator._async_update_data()
    finally:
        await coordinator.async_shutdown()
        await tempo.async_shutdown()

    assert data["contract"] == CONTRACT_HEURES_CREUSES
    assert data["price"] == pytest.approx(0.2068)
    assert data["current_period"] == "HC"
    assert data["is_hc"] is True
    assert data["tempo_color"] is None
