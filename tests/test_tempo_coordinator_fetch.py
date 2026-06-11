"""Async fetch tests for TempoDataCoordinator."""

from __future__ import annotations

import re

import aioresponses
import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.tempo_rte_forecast.const import (
    COULEUR_TEMPO_API_BASE,
    CONF_TEMPO_RETRY_DELAY,
    RTE_API_FULL_URL,
    RTE_API_URL,
)
from custom_components.tempo_rte_forecast.tempo_coordinator import TempoDataCoordinator
from tests.conftest import TODAY, TOMORROW


@pytest.mark.asyncio
async def test_async_update_data_from_rte_light(
    hass, mock_config_entry, fixed_tempo_dates
) -> None:
    """Complete J/J+1 from tempoLight only."""
    with aioresponses.aioresponses() as mocked:
        mocked.get(
            RTE_API_URL,
            payload={"values": {TODAY: "blue", TOMORROW: "white"}},
        )
        coordinator = TempoDataCoordinator(hass, mock_config_entry)
        try:
            data = await coordinator._async_update_data()
        finally:
            await coordinator.async_shutdown()

    assert data[TODAY] == "blue"
    assert data[TOMORROW] == "white"


@pytest.mark.asyncio
async def test_async_update_data_couleur_tempo_buffer_fills_j_plus_1(
    hass, mock_config_entry, fixed_tempo_dates
) -> None:
    """Missing J+1 on tempoLight is filled via api-couleur-tempo.fr."""
    with aioresponses.aioresponses() as mocked:
        mocked.get(RTE_API_URL, payload={"values": {TODAY: "blue"}})
        mocked.get(
            re.compile(rf"{re.escape(COULEUR_TEMPO_API_BASE)}/api/joursTempo.*"),
            payload=[{"dateJour": TOMORROW, "codeJour": 3}],
        )
        coordinator = TempoDataCoordinator(hass, mock_config_entry)
        try:
            data = await coordinator._async_update_data()
        finally:
            await coordinator.async_shutdown()

    assert data[TODAY] == "blue"
    assert data[TOMORROW] == "red"


@pytest.mark.asyncio
async def test_async_update_data_falls_back_to_rte_full(
    hass, mock_config_entry, fixed_tempo_dates
) -> None:
    """RTE Full calendar is used when Light and buffer are incomplete."""
    full_url = RTE_API_FULL_URL.format(season="2025-2026")
    with aioresponses.aioresponses() as mocked:
        mocked.get(RTE_API_URL, payload={"values": {TODAY: "unknown"}})
        mocked.get(
            re.compile(rf"{re.escape(COULEUR_TEMPO_API_BASE)}/api/joursTempo.*"),
            payload=[],
        )
        mocked.get(
            full_url,
            payload={"values": {TODAY: "white", TOMORROW: "blue"}},
        )
        coordinator = TempoDataCoordinator(hass, mock_config_entry)
        try:
            data = await coordinator._async_update_data()
        finally:
            await coordinator.async_shutdown()

    assert data[TODAY] == "white"
    assert data[TOMORROW] == "blue"


@pytest.mark.asyncio
async def test_async_update_data_raises_without_cache(
    hass, mock_config_entry, fixed_tempo_dates
) -> None:
    """All sources failing without cache raises UpdateFailed with retry_after."""
    full_url = RTE_API_FULL_URL.format(season="2025-2026")
    with aioresponses.aioresponses() as mocked:
        mocked.get(RTE_API_URL, status=503, body="maintenance")
        mocked.get(
            re.compile(rf"{re.escape(COULEUR_TEMPO_API_BASE)}/api/joursTempo.*"),
            status=503,
            body="maintenance",
        )
        mocked.get(full_url, status=503, body="maintenance")
        coordinator = TempoDataCoordinator(hass, mock_config_entry)
        try:
            with pytest.raises(UpdateFailed, match="no cached data"):
                await coordinator._async_update_data()
        finally:
            await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_async_update_data_serves_cache_on_failure(
    hass, mock_config_entry, fixed_tempo_dates
) -> None:
    """Cached colors are kept when refresh fails."""
    full_url = RTE_API_FULL_URL.format(season="2025-2026")
    with aioresponses.aioresponses() as mocked:
        mocked.get(RTE_API_URL, status=503, body="maintenance")
        mocked.get(
            re.compile(rf"{re.escape(COULEUR_TEMPO_API_BASE)}/api/joursTempo.*"),
            status=503,
            body="maintenance",
        )
        mocked.get(full_url, status=503, body="maintenance")
        coordinator = TempoDataCoordinator(hass, mock_config_entry)
        coordinator._cached_data = {TODAY: "blue", TOMORROW: "white"}
        try:
            with pytest.raises(UpdateFailed, match="serving cached data") as exc_info:
                await coordinator._async_update_data()
        finally:
            await coordinator.async_shutdown()

    assert exc_info.value.retry_after == float(
        mock_config_entry.options[CONF_TEMPO_RETRY_DELAY] * 60
    )
