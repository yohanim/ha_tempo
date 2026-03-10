"""
EDF Tempo integration for Home Assistant
Copyright (C) 2025 Christophe Bansart
"""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr

from .const import (
    DOMAIN
)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Migrate unique IDs if necessary
    await _async_migrate_unique_ids(hass, entry)
    
    # Cleanup old ghost devices
    await _async_cleanup_devices(hass, entry)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
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
    """Remove old devices that have no entities."""
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    
    # Old device was identified by (DOMAIN, "forecast")
    old_device = dev_reg.async_get_device(identifiers={(DOMAIN, "forecast")})
    
    if old_device:
        # Check if any entities are still linked to this device
        entities = er.async_entries_for_device(ent_reg, old_device.id)
        if not entities:
            dev_reg.async_remove_device(old_device.id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload integration."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
