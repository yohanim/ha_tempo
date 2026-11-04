"""
EDF Tempo integration for Home Assistant
Copyright (C) 2025 Christophe Bansart
"""
from __future__ import annotations

from dataclasses import dataclass
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN
)
from .devices import async_register_main_device
from .forecast_coordinator import ForecastCoordinator
from .issues import (
    async_check_offpeak_ranges,
    async_delete_all_issues,
    async_delete_api_issues,
    async_track_api_outage,
)
from .prices_coordinator import PriceCoordinator
from .tempo_coordinator import TempoDataCoordinator

PLATFORMS = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

DATA_REFRESH_SERVICE_REGISTERED = "refresh_service_registered"


async def _async_ensure_refresh_service(hass: HomeAssistant) -> None:
    """Register tempo_rte_forecast.refresh once (manual API re-fetch)."""
    reg = hass.data.setdefault(DOMAIN, {})
    if reg.get(DATA_REFRESH_SERVICE_REGISTERED):
        return

    async def async_handle_refresh(_call: ServiceCall) -> None:
        for ent in hass.config_entries.async_entries(DOMAIN):
            if ent.state != ConfigEntryState.LOADED:
                continue
            runtime = ent.runtime_data
            if runtime is None:
                continue
            title = ent.title
            try:
                await runtime.forecast_coordinator.async_refresh()
            except Exception as err:
                _LOGGER.warning("%s: manual forecast refresh failed: %s", title, err)
            try:
                await runtime.tempo_coordinator.async_refresh()
            except Exception as err:
                _LOGGER.warning("%s: manual Tempo refresh failed: %s", title, err)
            try:
                await runtime.price_coordinator.async_force_prices_update()
                await runtime.price_coordinator.async_refresh()
            except Exception as err:
                _LOGGER.warning("%s: manual price refresh failed: %s", title, err)

    hass.services.async_register(
        DOMAIN,
        "refresh",
        async_handle_refresh,
        schema=vol.Schema({}),
    )
    reg[DATA_REFRESH_SERVICE_REGISTERED] = True


def _remove_refresh_service_if_last(hass: HomeAssistant, unloaded_entry_id: str) -> None:
    """Unregister the service when no loaded config entries remain."""
    others = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.state == ConfigEntryState.LOADED
        and e.entry_id != unloaded_entry_id
    ]
    if others:
        return
    hass.services.async_remove(DOMAIN, "refresh")
    hass.data.get(DOMAIN, {}).pop(DATA_REFRESH_SERVICE_REGISTERED, None)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry to the current version."""
    if entry.version < 2:
        _LOGGER.info("Migrating config entry from version %s to 2", entry.version)
        await _async_migrate_unique_ids(hass, entry)
        hass.config_entries.async_update_entry(entry, version=2)
        _LOGGER.info("Migration to version 2 complete")
    return True


@dataclass
class TempoRuntimeData:
    """Runtime data for a config entry."""

    tempo_coordinator: TempoDataCoordinator
    forecast_coordinator: ForecastCoordinator
    price_coordinator: PriceCoordinator
    main_device_id: str


type TempoConfigEntry = ConfigEntry[TempoRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: TempoConfigEntry) -> bool:
    """Setup integration from a config entry."""
    # Cleanup old ghost devices (idempotent, no-op once the device is gone)
    await _async_cleanup_devices(hass, entry)

    tempo_coordinator = TempoDataCoordinator(hass, entry)
    try:
        await tempo_coordinator.async_load_cache()
    except Exception as err:
        _LOGGER.warning("Failed to restore cached Tempo colors: %s", err)
    forecast_coordinator = ForecastCoordinator(hass, entry)

    # Forecast first so Open-DPE data exists if RTE is down (maintenance, etc.).
    try:
        await forecast_coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        _LOGGER.warning(
            "Open-DPE forecast not ready at startup; continuing. "
            "Forecast entities may be unavailable until the next refresh."
        )

    try:
        await tempo_coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        _LOGGER.warning(
            "RTE Tempo not ready at startup; continuing. "
            "RTE-backed entities may be unavailable until the API recovers."
        )

    price_coordinator = PriceCoordinator(hass, entry, tempo_coordinator)
    try:
        await price_coordinator.async_load_cache()
    except Exception as err:
        _LOGGER.warning("Failed to restore cached prices: %s", err)
    # Cache is restored; safe to kick off the background fetch now, no race.
    price_coordinator.async_schedule_initial_fetch()
    try:
        await price_coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        _LOGGER.warning(
            "Price coordinator not ready at startup; continuing."
        )

    entry.runtime_data = TempoRuntimeData(
        tempo_coordinator=tempo_coordinator,
        forecast_coordinator=forecast_coordinator,
        price_coordinator=price_coordinator,
        # Child devices (forecast, prices) reference the main device by id.
        main_device_id=async_register_main_device(hass, entry),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Repair issues: long API outages (hidden by cached values) and invalid
    # off-peak ranges saved by older versions.
    entry.async_on_unload(
        async_track_api_outage(hass, tempo_coordinator, "rte", "RTE")
    )
    entry.async_on_unload(
        async_track_api_outage(hass, forecast_coordinator, "opendpe", "Open DPE")
    )
    async_check_offpeak_ranges(hass, entry)

    await _async_ensure_refresh_service(hass)

    return True

async def _async_migrate_unique_ids(hass: HomeAssistant, entry: ConfigEntry):
    """Migrate old unique IDs to new entry_id based ones."""
    ent_reg = er.async_get(hass)
    entry_id = entry.entry_id
    
    entries = er.async_entries_for_config_entry(ent_reg, entry_id)
    
    for entity in entries:
        old_unique_id = entity.unique_id
        new_unique_id = None
        
        if old_unique_id.startswith(f"{DOMAIN}_J"):
            suffix = old_unique_id.replace(f"{DOMAIN}_J", "")
            new_unique_id = f"{entry_id}_J{suffix}"
            
        elif old_unique_id.startswith(f"{DOMAIN}_forecast_opendpe"):
            suffix = old_unique_id.replace(f"{DOMAIN}_forecast_opendpe", "")
            new_unique_id = f"{entry_id}_forecast_opendpe{suffix}"

        elif old_unique_id == f"{DOMAIN}_current_price":
            new_unique_id = f"{entry_id}_current_price"
            
        elif old_unique_id.startswith(f"{DOMAIN}_tempo_") or old_unique_id.startswith(f"{DOMAIN}_base_") or old_unique_id.startswith(f"{DOMAIN}_heures_creuses_"):
            suffix = old_unique_id.replace(f"{DOMAIN}_", "")
            new_unique_id = f"{entry_id}_{suffix}"

        if new_unique_id and new_unique_id != old_unique_id:
            if not ent_reg.async_get_entity_id(entity.domain, entity.platform, new_unique_id):
                ent_reg.async_update_entity(entity.entity_id, new_unique_id=new_unique_id)

async def _async_cleanup_devices(hass: HomeAssistant, entry: ConfigEntry):
    """Remove old devices that have no entities.

    Scoped to this entry (not a global identifiers lookup) because HA's
    single-entry-per-device model already removes a device automatically
    once its last owning config entry is gone, so a ghost device can only
    ever belong to the entry currently being set up.
    """
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        if (DOMAIN, "forecast") in device.identifiers:
            if not er.async_entries_for_device(ent_reg, device.id):
                dev_reg.async_remove_device(device.id)

async def async_unload_entry(hass: HomeAssistant, entry: TempoConfigEntry) -> bool:
    """Unload integration."""
    entry_id = entry.entry_id
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and hasattr(entry, "runtime_data"):
        await entry.runtime_data.tempo_coordinator.async_shutdown()
        await entry.runtime_data.forecast_coordinator.async_shutdown()
        await entry.runtime_data.price_coordinator.async_shutdown()
    if unload_ok:
        _remove_refresh_service_if_last(hass, entry_id)
        async_delete_api_issues(hass)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete this entry's cached data stores from disk."""
    await Store(hass, 1, f"{DOMAIN}_{entry.entry_id}_prices_cache").async_remove()
    await Store(hass, 1, f"{DOMAIN}_{entry.entry_id}_tempo_cache").async_remove()
    async_delete_all_issues(hass)
