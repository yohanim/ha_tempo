from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO, ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEVICE_NAME, DEVICE_MANUFACTURER, DEVICE_MODEL
from .tariff_coordinator import TariffCoordinator

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Tarifs basés sur les options de l'intégration"

class TariffSensor(CoordinatorEntity[TariffCoordinator], SensorEntity):
    """Sensor for the current electricity tariff."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
    _attr_icon = "mdi:currency-eur"
    _attr_has_entity_name = True

    def __init__(self, coordinator: TariffCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{DOMAIN}_current_tariff"
        self._attr_name = "Tarif actuel"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, "forecast")}, # Using same device as others
            name=DEVICE_NAME,
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
        )

    @property
    def native_value(self) -> float | None:
        """Return the current tariff price."""
        if self.coordinator.data:
            return self.coordinator.data.get("price")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}

        data = self.coordinator.data
        attributes = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            "contract": data.get("contract"),
            "is_hc": data.get("is_hc"),
            "current_period": data.get("current_period"),
            "last_update": data.get("last_update"),
            "tariffs_last_update": data.get("tariffs_last_update"),
        }
        if data.get("contract") == "Tempo":
            attributes["tempo_color"] = data.get("tempo_color")

        return attributes

class SpecificTariffSensor(CoordinatorEntity[TariffCoordinator], SensorEntity):
    """Sensor for a specific tariff price component (e.g. 'Tempo Red HP')."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
    _attr_icon = "mdi:currency-eur"
    _attr_has_entity_name = True

    def __init__(self, coordinator: TariffCoordinator, entry: ConfigEntry, key: str, color: str | None = None):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._key = key  # "HP" or "HC"
        self._color = color  # "BLUE", "WHITE", "RED" or None

        # Construct unique ID and Name based on contract and variant
        contract_name = coordinator.data.get("contract", "unknown")
        contract_slug = contract_name.lower().replace(" ", "_")
        
        slug_parts = [contract_slug]
        name_parts = ["Prix"]

        if color:
            color_map = {"BLUE": "Bleu", "WHITE": "Blanc", "RED": "Rouge"}
            color_fr = color_map.get(color, color)
            slug_parts.append(color.lower())
            name_parts.append(color_fr)
        
        slug_parts.append(key.lower())
        name_parts.append(key)

        self._attr_unique_id = f"{DOMAIN}_{'_'.join(slug_parts)}"
        self._attr_name = " ".join(name_parts)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, "forecast")},
            name=DEVICE_NAME,
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
        )

    @property
    def native_value(self) -> float | None:
        """Return the specific tariff price."""
        if not self.coordinator.data:
            return None
            
        prices = self.coordinator.data.get("contract_prices", {})
        
        if self._color:
            # Tempo structure: {"BLUE": {"HP": x, "HC": y}, ...}
            return prices.get(self._color, {}).get(self._key)
        
        # Base/HC structure: {"HP": x, "HC": y}
        return prices.get(self._key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
            
        data = self.coordinator.data
        attributes = {
            "active": False,
            "subscribed_power": data.get("subscribed_power"),
        }
        
        current_period = data.get("current_period")
        contract = data.get("contract")

        if self._color:
            # Tempo
            current_color = data.get("tempo_color")
            if current_color == self._color and current_period == self._key:
                attributes["active"] = True
        else:
            # Base or HC
            if contract == "Base":
                attributes["active"] = True
            elif current_period == self._key:
                attributes["active"] = True
                
        return attributes