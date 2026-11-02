"""Helpers for DataUpdateCoordinator when update_interval is None.

Core schedules ``UpdateFailed(retry_after=...)`` only if ``update_interval`` is set
(see ``homeassistant.helpers.update_coordinator._schedule_refresh``). This integration
uses ``update_interval=None`` and ``async_track_time_change`` instead; the mixin
below schedules the one-shot retry itself.

The retry goes through the public ``async_call_later`` helper and core's
``_handle_refresh_interval`` (debouncer lock, ``scheduled=True``), not the
name-mangled ``__wrap_handle_refresh_interval`` callback: HA 2026.10.0 changed
its signature to ``(self, _: HassJob)``, which broke a direct ``loop.call_at``.

Sensors override ``available`` based on cached values where applicable so a failed
refresh (``last_update_success`` false) does not hide stale-but-valid data.
"""

from __future__ import annotations

from homeassistant.core import HassJob, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import UpdateFailed


class RetryWhenNoUpdateIntervalMixin:
    """Honor ``retry_after`` when ``update_interval`` is ``None``.

    ``retry_after`` comes from ``UpdateFailed`` or is set directly on
    ``_retry_after`` by ``_async_update_data`` for a partial success.
    """

    async def async_config_entry_first_refresh(self) -> None:
        """First refresh, then arm the retry core skips during setup.

        Core ignores ``UpdateFailed.retry_after`` on the first refresh and only
        calls ``_schedule_refresh`` once entities listen, which they don't yet.
        """
        try:
            await super().async_config_entry_first_refresh()  # type: ignore[misc]
        finally:
            err = self.last_exception
            if (
                not self.last_update_success
                and isinstance(err, UpdateFailed)
                and err.retry_after is not None
            ):
                self._retry_after = err.retry_after
            self._schedule_refresh()

    @callback
    def _schedule_refresh(self) -> None:
        if self._update_interval_seconds is not None:
            super()._schedule_refresh()  # type: ignore[misc]
            return

        if self._retry_after is None:
            return

        if self.config_entry and self.config_entry.pref_disable_polling:
            return

        # Stored in _unsub_refresh so core's _async_unsub_refresh (next refresh,
        # shutdown) cancels a pending retry.
        self._async_unsub_refresh()
        delay = self._retry_after
        self._retry_after = None
        self._unsub_refresh = async_call_later(
            self.hass,
            delay,
            HassJob(
                self._handle_refresh_interval,
                f"{self.name} retry",
                cancel_on_shutdown=True,
            ),
        )
