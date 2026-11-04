"""Repair issues (Settings > Repairs) for problems the sensors hide.

Sensors keep showing cached values when an API fails, so a long outage would
otherwise go unnoticed. Issues are created without ``config_entry_id`` (HA
2026.11+ only); they are deleted on unload and on entry removal instead.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CONTRACT,
    CONF_OFFPEAK_RANGES,
    CONTRACT_BASE,
    DEFAULT_CONTRACT,
    DEFAULT_OFFPEAK_RANGES,
    DOMAIN,
)
from .utils import invalid_offpeak_parts, normalize_contract

API_OUTAGE_THRESHOLD = timedelta(hours=24)

ISSUE_INVALID_OFFPEAK = "invalid_offpeak_ranges"
API_KEYS = ("rte", "opendpe")


def api_issue_id(api_key: str) -> str:
    """Issue id of an API outage (single-instance integration)."""
    return f"api_unavailable_{api_key}"


@callback
def async_track_api_outage(
    hass: HomeAssistant,
    coordinator: DataUpdateCoordinator,
    api_key: str,
    api_name: str,
) -> CALLBACK_TYPE:
    """Raise a repair issue once the coordinator has failed for too long.

    The issue is deleted on the next successful update. Returns the unsubscribe.
    """
    failing_since: datetime | None = None
    issue_id = api_issue_id(api_key)

    @callback
    def _on_update() -> None:
        nonlocal failing_since
        if coordinator.last_update_success:
            failing_since = None
            ir.async_delete_issue(hass, DOMAIN, issue_id)
            return
        now = dt_util.utcnow()
        if failing_since is None:
            failing_since = now
        if now - failing_since >= API_OUTAGE_THRESHOLD:
            ir.async_create_issue(
                hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="api_unavailable",
                translation_placeholders={
                    "api": api_name,
                    "hours": str(int(API_OUTAGE_THRESHOLD.total_seconds() // 3600)),
                },
            )

    # The first refresh already ran: start the clock if it failed.
    _on_update()
    return coordinator.async_add_listener(_on_update)


@callback
def async_check_offpeak_ranges(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Raise or clear the issue for invalid stored off-peak ranges.

    The options form rejects invalid ranges, but values saved by older
    versions were never validated.
    """
    contract = normalize_contract(entry.options.get(CONF_CONTRACT, DEFAULT_CONTRACT))
    invalid = []
    if contract != CONTRACT_BASE:
        invalid = invalid_offpeak_parts(
            entry.options.get(CONF_OFFPEAK_RANGES, DEFAULT_OFFPEAK_RANGES)
        )
    if not invalid:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_INVALID_OFFPEAK)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_INVALID_OFFPEAK,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_INVALID_OFFPEAK,
        translation_placeholders={"ranges": ", ".join(invalid)},
    )


@callback
def async_delete_api_issues(hass: HomeAssistant) -> None:
    """Delete API outage issues (entry unloaded: nothing is fetching anymore)."""
    for api_key in API_KEYS:
        ir.async_delete_issue(hass, DOMAIN, api_issue_id(api_key))


@callback
def async_delete_all_issues(hass: HomeAssistant) -> None:
    """Delete every issue of the integration (entry removed)."""
    async_delete_api_issues(hass)
    ir.async_delete_issue(hass, DOMAIN, ISSUE_INVALID_OFFPEAK)
