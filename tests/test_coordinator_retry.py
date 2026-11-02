"""Tests for coordinator retry mixin."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.tempo_rte_forecast.coordinator_retry import (
    RetryWhenNoUpdateIntervalMixin,
)

RETRY_SECONDS = 1800.0


class _RetryCoordinator(RetryWhenNoUpdateIntervalMixin, DataUpdateCoordinator):
    """Coordinator failing with retry_after until ``fail`` is cleared."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass, MagicMock(), name="retry test", config_entry=None, update_interval=None
        )
        self.fail = True
        self.calls = 0

    async def _async_update_data(self) -> dict:
        self.calls += 1
        if self.fail:
            raise UpdateFailed("still missing", retry_after=RETRY_SECONDS)
        return {"ok": True}


async def test_retry_after_fires_and_repeats_until_success(hass: HomeAssistant) -> None:
    """Regression (HA 2026.10): the scheduled retry must actually run the refresh."""
    coordinator = _RetryCoordinator(hass)
    unsub = coordinator.async_add_listener(lambda: None)

    await coordinator.async_refresh()
    assert coordinator.calls == 1
    assert coordinator.last_update_success is False

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=RETRY_SECONDS + 1))
    await hass.async_block_till_done()
    assert coordinator.calls == 2

    coordinator.fail = False
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=2 * RETRY_SECONDS + 2))
    await hass.async_block_till_done()
    assert coordinator.calls == 3
    assert coordinator.last_update_success is True

    # Success: no further retry is scheduled.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=4 * RETRY_SECONDS))
    await hass.async_block_till_done()
    assert coordinator.calls == 3

    unsub()
    await coordinator.async_shutdown()


class _FirstRefreshCoordinator(_RetryCoordinator):
    """Runs the core first-refresh path without a real config entry in SETUP_IN_PROGRESS."""

    def __init__(self, hass: HomeAssistant, *, partial: bool = False) -> None:
        super().__init__(hass)
        self.partial = partial

    async def _async_update_data(self) -> dict:
        if self.partial:
            self.calls += 1
            self._retry_after = RETRY_SECONDS
            return {"partial": True}
        return await super()._async_update_data()

    async def _async_config_entry_first_refresh(self) -> None:
        # Same _async_refresh flags as core's first refresh.
        await self._async_refresh(
            log_failures=False, raise_on_auth_failed=True, raise_on_entry_error=True
        )
        if not self.last_update_success:
            raise ConfigEntryNotReady from self.last_exception


@pytest.mark.parametrize("partial", [False, True])
async def test_first_refresh_arms_retry(hass: HomeAssistant, partial: bool) -> None:
    """Core skips retry_after at setup and has no listeners yet; the mixin arms it."""
    coordinator = _FirstRefreshCoordinator(hass, partial=partial)

    if partial:
        await coordinator.async_config_entry_first_refresh()
    else:
        with pytest.raises(ConfigEntryNotReady):
            await coordinator.async_config_entry_first_refresh()
    assert coordinator.calls == 1

    unsub = coordinator.async_add_listener(lambda: None)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=RETRY_SECONDS + 1))
    await hass.async_block_till_done()
    assert coordinator.calls == 2

    unsub()
    await coordinator.async_shutdown()


async def test_first_refresh_success_does_not_arm_retry(hass: HomeAssistant) -> None:
    coordinator = _FirstRefreshCoordinator(hass)
    coordinator.fail = False

    await coordinator.async_config_entry_first_refresh()
    assert coordinator._unsub_refresh is None

    await coordinator.async_shutdown()


def _make_mock_coordinator(*, retry_after: float | None = RETRY_SECONDS) -> MagicMock:
    coordinator = MagicMock()
    coordinator._update_interval_seconds = None
    coordinator._retry_after = retry_after
    coordinator.config_entry.pref_disable_polling = False
    coordinator._handle_refresh_interval = AsyncMock()
    return coordinator


def test_schedule_refresh_noop_without_retry_after() -> None:
    coordinator = _make_mock_coordinator(retry_after=None)

    with patch(
        "custom_components.tempo_rte_forecast.coordinator_retry.async_call_later"
    ) as call_later:
        RetryWhenNoUpdateIntervalMixin._schedule_refresh(coordinator)

    call_later.assert_not_called()


def test_schedule_refresh_noop_when_polling_disabled() -> None:
    coordinator = _make_mock_coordinator()
    coordinator.config_entry.pref_disable_polling = True

    with patch(
        "custom_components.tempo_rte_forecast.coordinator_retry.async_call_later"
    ) as call_later:
        RetryWhenNoUpdateIntervalMixin._schedule_refresh(coordinator)

    call_later.assert_not_called()
