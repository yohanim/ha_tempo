"""Helpers for DataUpdateCoordinator when update_interval is None.

Core schedules ``UpdateFailed(retry_after=...)`` only if ``update_interval`` is set
(see ``homeassistant.helpers.update_coordinator._schedule_refresh``). This integration
uses ``update_interval=None`` and ``async_track_time_change`` instead; the mixin
below mirrors the core timer logic for the one-shot retry case.

Sensors override ``available`` based on cached values where applicable so a failed
refresh (``last_update_success`` false) does not hide stale-but-valid data.
"""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


def _coordinator_wrap_handle_refresh(coordinator: DataUpdateCoordinator):
    """Bound callback for DataUpdateCoordinator.__wrap_handle_refresh_interval.

    ``self.__wrap_handle_refresh_interval`` cannot be used inside this mixin: Python
    would mangle it to ``_RetryWhenNoUpdateIntervalMixin__...`` instead of the
    real ``_DataUpdateCoordinator__wrap_handle_refresh_interval`` on the instance.
    """
    return getattr(coordinator, "_DataUpdateCoordinator__wrap_handle_refresh_interval")


class RetryWhenNoUpdateIntervalMixin:
    """Honor ``retry_after`` from ``UpdateFailed`` when ``update_interval`` is ``None``."""

    @callback
    def _schedule_refresh(self) -> None:
        if self._update_interval_seconds is not None:
            super()._schedule_refresh()  # type: ignore[misc]
            return

        if self._retry_after is None:
            return

        if self.config_entry and self.config_entry.pref_disable_polling:
            return

        self._async_unsub_refresh()
        hass = self.hass
        loop = hass.loop
        update_interval = self._retry_after
        self._retry_after = None
        next_refresh = int(loop.time()) + self._microsecond + update_interval
        wrap = _coordinator_wrap_handle_refresh(self)
        self._unsub_refresh = loop.call_at(next_refresh, wrap).cancel
