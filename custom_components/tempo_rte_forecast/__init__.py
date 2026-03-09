"""
EDF Tempo integration for Home Assistant
Copyright (C) 2025 Christophe Bansart
"""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    DOMAIN
)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configuration de l'intégration depuis une config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Migration des identifiants uniques (si nécessaire)
    await _async_migrate_unique_ids(hass, entry)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def _async_migrate_unique_ids(hass: HomeAssistant, entry: ConfigEntry):
    """Migrate old unique IDs to new entry_id based ones."""
    ent_reg = er.async_get(hass)
    entry_id = entry.entry_id
    
    # Liste des anciens patterns et nouveaux patterns attendus
    # Old: tempo_rte_forecast_J... -> New: {entry_id}_J...
    # Old: tempo_rte_forecast_current_price -> New: {entry_id}_current_price
    # Old: tempo_rte_forecast_tempo_blue_hp -> New: {entry_id}_tempo_blue_hp
    
    entries = er.async_entries_for_config_entry(ent_reg, entry_id)
    
    for entity in entries:
        old_unique_id = entity.unique_id
        new_unique_id = None
        
        # Pattern 1: J+X sensors
        if old_unique_id.startswith(f"{DOMAIN}_J"):
            suffix = old_unique_id.replace(f"{DOMAIN}_J", "")
            new_unique_id = f"{entry_id}_J{suffix}"
            
        # Pattern 2: Forecast OpenDPE
        elif old_unique_id.startswith(f"{DOMAIN}_forecast_opendpe"):
            suffix = old_unique_id.replace(f"{DOMAIN}_forecast_opendpe", "")
            new_unique_id = f"{entry_id}_forecast_opendpe{suffix}"

        # Pattern 3: Current Price
        elif old_unique_id == f"{DOMAIN}_current_price":
            new_unique_id = f"{entry_id}_current_price"
            
        # Pattern 4: Specific Price
        elif old_unique_id.startswith(f"{DOMAIN}_tempo_") or old_unique_id.startswith(f"{DOMAIN}_base_") or old_unique_id.startswith(f"{DOMAIN}_heures_creuses_"):
             # remove domain prefix
            suffix = old_unique_id.replace(f"{DOMAIN}_", "")
            new_unique_id = f"{entry_id}_{suffix}"

        if new_unique_id and new_unique_id != old_unique_id:
            # Check if new ID already exists (collision)
            if not ent_reg.async_get_entity_id(entity.domain, entity.platform, new_unique_id):
                ent_reg.async_update_entity(entity.entity_id, new_unique_id=new_unique_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Déchargement de l'intégration."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
