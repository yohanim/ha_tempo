"""Shared pytest configuration for tempo_rte_forecast."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Iterator
from dataclasses import dataclass, field
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.tempo_rte_forecast.const import (
    CONF_CONTRACT,
    CONTRACT_TEMPO,
    DEFAULT_CONTRACT,
    CONF_EDF_TEMPO_COLOR_REFRESH_TIME,
    CONF_FORECAST_RETRY_DELAY,
    CONF_OPENDPE_SERVICE_TYPE,
    CONF_RTE_TEMPO_COLOR_REFRESH_TIME,
    CONF_TEMPO_DAY_CHANGE_TIME,
    CONF_TEMPO_RETRY_DELAY,
    DEFAULT_EDF_TEMPO_COLOR_REFRESH_TIME,
    DEFAULT_RTE_TEMPO_COLOR_REFRESH_TIME,
    DOMAIN,
    FORECAST_RETRY_DELAY_MINUTES,
    OPENDPE_SERVICE_LIGHT,
    TEMPO_DAY_CHANGE_TIME,
    TEMPO_RETRY_DELAY_MINUTES,
)

TODAY = "2026-06-11"
TOMORROW = "2026-06-12"


@dataclass
class MockConfigEntry:
    """Minimal config entry stub for coordinator tests."""

    domain: str
    title: str = "Tempo test"
    entry_id: str = "test-entry-id"
    data: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)
    pref_disable_polling: bool = False


@pytest.fixture(autouse=True)
def _disable_frame_usage_reporting() -> Iterator[None]:
    """DataUpdateCoordinator calls frame.report_usage during __init__ in HA 2026+."""
    with patch("homeassistant.helpers.frame.report_usage"):
        yield


@pytest.fixture
async def hass(tmp_path) -> AsyncGenerator[HomeAssistant]:
    """Start a lightweight Home Assistant core instance."""
    import aiohttp

    config_dir = tmp_path / "ha_config"
    config_dir.mkdir()
    hass = HomeAssistant(str(config_dir))
    await hass.async_start()
    session = aiohttp.ClientSession()
    patch_targets = (
        "custom_components.tempo_rte_forecast.tempo_coordinator.async_get_clientsession",
        "custom_components.tempo_rte_forecast.forecast_coordinator.async_get_clientsession",
        "custom_components.tempo_rte_forecast.prices_coordinator.async_get_clientsession",
    )
    with patch(patch_targets[0], return_value=session), patch(
        patch_targets[1], return_value=session
    ), patch(patch_targets[2], return_value=session):
        yield hass
    await session.close()
    await hass.async_stop()


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Config entry with default integration options."""
    return MockConfigEntry(
        domain=DOMAIN,
        options={
            CONF_TEMPO_DAY_CHANGE_TIME: TEMPO_DAY_CHANGE_TIME,
            CONF_RTE_TEMPO_COLOR_REFRESH_TIME: DEFAULT_RTE_TEMPO_COLOR_REFRESH_TIME,
            CONF_EDF_TEMPO_COLOR_REFRESH_TIME: DEFAULT_EDF_TEMPO_COLOR_REFRESH_TIME,
            CONF_TEMPO_RETRY_DELAY: TEMPO_RETRY_DELAY_MINUTES,
            CONF_FORECAST_RETRY_DELAY: FORECAST_RETRY_DELAY_MINUTES,
            CONF_OPENDPE_SERVICE_TYPE: OPENDPE_SERVICE_LIGHT,
            CONF_CONTRACT: CONTRACT_TEMPO,
        },
    )


@pytest.fixture
def fixed_tempo_dates() -> Iterator[None]:
    """Pin Tempo calendar days used by coordinators during a test."""

    def _tempo_date(offset_days: int = 0, *_args, **_kwargs) -> str:
        return TODAY if offset_days == 0 else TOMORROW

    patches = [
        patch(
            "custom_components.tempo_rte_forecast.tempo_coordinator.get_tempo_date",
            side_effect=_tempo_date,
        ),
        patch(
            "custom_components.tempo_rte_forecast.prices_coordinator.get_tempo_date",
            side_effect=_tempo_date,
        ),
    ]
    for item in patches:
        item.start()
    yield
    for item in patches:
        item.stop()
