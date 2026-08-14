"""Async fetch tests for ForecastCoordinator."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.tempo_rte_forecast.const import CONF_FORECAST_RETRY_DELAY
from custom_components.tempo_rte_forecast.forecast_coordinator import (
    ForecastCoordinator,
    async_fetch_opendpe_forecast,
)
from custom_components.tempo_rte_forecast.sensor_types import ForecastSensor
from tests.conftest import make_ctx_response


@pytest.mark.asyncio
async def test_opendpe_fetch_success(hass, mock_config_entry) -> None:
    """Open-DPE light JSON is parsed into ForecastSensor entries."""
    payload = [
        {"date": "2026-06-12", "couleur": "bleu", "probability": 1},
        {"date": "2026-06-13", "couleur": "blanc", "probability": 1},
    ]
    coordinator = ForecastCoordinator(hass, mock_config_entry)
    coordinator.session = MagicMock()
    coordinator.session.get = MagicMock(return_value=make_ctx_response(payload=payload))
    try:
        forecasts = await async_fetch_opendpe_forecast(coordinator)
    finally:
        await coordinator.async_shutdown()

    assert "2026-06-12" in forecasts
    assert isinstance(forecasts["2026-06-12"], ForecastSensor)
    assert forecasts["2026-06-12"].color == "bleu"
    assert forecasts["2026-06-13"].color == "blanc"


@pytest.mark.asyncio
async def test_opendpe_fetch_http_error_without_cache(
    hass, mock_config_entry
) -> None:
    """HTTP failure without cache raises UpdateFailed."""
    coordinator = ForecastCoordinator(hass, mock_config_entry)
    coordinator.session = MagicMock()
    coordinator.session.get = MagicMock(
        return_value=make_ctx_response(status=502, text="bad gateway")
    )
    try:
        with pytest.raises(UpdateFailed, match="no cached data"):
            await async_fetch_opendpe_forecast(coordinator)
    finally:
        await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_opendpe_fetch_http_error_with_cache(
    hass, mock_config_entry
) -> None:
    """HTTP failure with cache raises UpdateFailed but keeps retry_after."""
    cached = ForecastSensor(
        date=date(2026, 6, 12),
        short_date="12/06",
        day="ven.",
        color="bleu",
        probability=100,
    )
    coordinator = ForecastCoordinator(hass, mock_config_entry)
    coordinator._cached_data = {"2026-06-12": cached}
    coordinator.session = MagicMock()
    coordinator.session.get = MagicMock(
        return_value=make_ctx_response(status=502, text="bad gateway")
    )
    try:
        with pytest.raises(UpdateFailed, match="serving cached data") as exc_info:
            await async_fetch_opendpe_forecast(coordinator)
    finally:
        await coordinator.async_shutdown()

    assert exc_info.value.retry_after == float(
        mock_config_entry.options[CONF_FORECAST_RETRY_DELAY] * 60
    )
