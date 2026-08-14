"""Async fetch tests for TempoDataCoordinator."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.tempo_rte_forecast.const import (
    CONF_TEMPO_RETRY_DELAY,
    COULEUR_TEMPO_API_BASE,
    RTE_API_FULL_URL,
    RTE_API_URL,
)
from custom_components.tempo_rte_forecast.tempo_coordinator import TempoDataCoordinator
from tests.conftest import TODAY, TOMORROW, make_ctx_response


def _url_dispatcher(**url_map):
    """Return a session.get callable that dispatches responses by URL substring."""
    def get(url, **kwargs):
        str_url = str(url)
        for pattern, resp in url_map.items():
            if pattern in str_url:
                return resp
        raise ValueError(f"Unexpected URL in test: {str_url}")
    return get


@pytest.mark.asyncio
async def test_async_update_data_from_rte_light(
    hass, mock_config_entry, fixed_tempo_dates
) -> None:
    """Complete J/J+1 from tempoLight only."""
    coordinator = TempoDataCoordinator(hass, mock_config_entry)
    coordinator.session = MagicMock()
    coordinator.session.get = MagicMock(
        return_value=make_ctx_response(payload={"values": {TODAY: "blue", TOMORROW: "white"}})
    )
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
    coordinator = TempoDataCoordinator(hass, mock_config_entry)
    coordinator.session = MagicMock()
    coordinator.session.get = _url_dispatcher(
        **{
            RTE_API_URL: make_ctx_response(payload={"values": {TODAY: "blue"}}),
            COULEUR_TEMPO_API_BASE: make_ctx_response(
                payload=[{"dateJour": TOMORROW, "codeJour": 3}]
            ),
        }
    )
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
    coordinator = TempoDataCoordinator(hass, mock_config_entry)
    coordinator.session = MagicMock()
    coordinator.session.get = _url_dispatcher(
        **{
            RTE_API_URL: make_ctx_response(payload={"values": {TODAY: "unknown"}}),
            COULEUR_TEMPO_API_BASE: make_ctx_response(payload=[]),
            full_url: make_ctx_response(
                payload={"values": {TODAY: "white", TOMORROW: "blue"}}
            ),
        }
    )
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
    coordinator = TempoDataCoordinator(hass, mock_config_entry)
    coordinator.session = MagicMock()
    coordinator.session.get = _url_dispatcher(
        **{
            RTE_API_URL: make_ctx_response(status=503, text="maintenance"),
            COULEUR_TEMPO_API_BASE: make_ctx_response(status=503, text="maintenance"),
            full_url: make_ctx_response(status=503, text="maintenance"),
        }
    )
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
    coordinator = TempoDataCoordinator(hass, mock_config_entry)
    coordinator._cached_data = {TODAY: "blue", TOMORROW: "white"}
    coordinator.session = MagicMock()
    coordinator.session.get = _url_dispatcher(
        **{
            RTE_API_URL: make_ctx_response(status=503, text="maintenance"),
            COULEUR_TEMPO_API_BASE: make_ctx_response(status=503, text="maintenance"),
            full_url: make_ctx_response(status=503, text="maintenance"),
        }
    )
    try:
        with pytest.raises(UpdateFailed, match="serving cached data") as exc_info:
            await coordinator._async_update_data()
    finally:
        await coordinator.async_shutdown()

    assert exc_info.value.retry_after == float(
        mock_config_entry.options[CONF_TEMPO_RETRY_DELAY] * 60
    )
