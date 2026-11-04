"""Device layout: one main device and child devices for its parts (HA 2026.9+).

- Main device: Tempo colors (J, J+1, J+1 synthesis).
- Child "forecast": Open-DPE forecast sensors.
- Child "prices": electricity price sensors.

Children reference the main device by registry id, so the main device is
registered in ``async_setup_entry`` before the platforms are forwarded.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import ChildDeviceInfo, DeviceInfo

from .const import DEVICE_MANUFACTURER, DEVICE_MODEL, DEVICE_NAME, DOMAIN

CHILD_FORECAST = "forecast"
CHILD_PRICES = "prices"


def main_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Device info of the main device (Tempo colors)."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=DEVICE_NAME,
        manufacturer=DEVICE_MANUFACTURER,
        model=DEVICE_MODEL,
    )


def async_register_main_device(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Register (or update) the main device and return its registry id."""
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=DEVICE_NAME,
        manufacturer=DEVICE_MANUFACTURER,
        model=DEVICE_MODEL,
    )
    return device.id


def child_device_info(entry: ConfigEntry, child: str) -> ChildDeviceInfo:
    """Device info of a child device, named through ``device`` translations."""
    return ChildDeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{child}")},
        parent_device_id=entry.runtime_data.main_device_id,
        translation_key=child,
    )
