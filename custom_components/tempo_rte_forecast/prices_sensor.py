from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COLORS, CONTRACT_TEMPO, CONTRACT_BASE
from .prices_coordinator import PriceCoordinator
from .devices import CHILD_PRICES, child_device_info
from .utils import get_icon_color, normalize_color, localized_color_label

class PriceSensor(CoordinatorEntity[PriceCoordinator], SensorEntity):
    """Sensor for the current electricity price."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
    _attr_has_entity_name = True
    _attr_translation_key = "price"
    _attr_attribution = "Prix basés sur les options de l'intégration"

    def __init__(self, coordinator: PriceCoordinator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_current_price"
        self._attr_device_info = child_device_info(entry, CHILD_PRICES)


    @property
    def native_value(self) -> float | None:
        """Return the current price."""
        if self.coordinator.data:
            return self.coordinator.data.get("price")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}

        data = self.coordinator.data
        tempo_color = data.get("tempo_color")
        color_key = normalize_color(tempo_color)
        
        attributes = {
            "contract": data.get("contract"),
            "is_hc": data.get("is_hc"),
            "is_hp": data.get("is_hp"),
            "current_period": data.get("current_period"),
            "last_update": data.get("last_update"),
            "prices_last_update": data.get("prices_last_update"),
            "icon_color": get_icon_color(self.entry.options, color_key),
            "is_blue_hp": data.get("is_blue_hp"),
            "is_blue_hc": data.get("is_blue_hc"),
            "is_white_hp": data.get("is_white_hp"),
            "is_white_hc": data.get("is_white_hc"),
            "is_red_hp": data.get("is_red_hp"),
            "is_red_hc": data.get("is_red_hc"),
            "next_period_change": data.get("next_period_change"),
        }
        if data.get("contract") == CONTRACT_TEMPO:
            attributes["tempo_color"] = tempo_color

        return attributes

class SpecificPriceSensor(CoordinatorEntity[PriceCoordinator], SensorEntity):
    """Sensor for a specific price component (e.g. 'Tempo Red HP')."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
    _attr_has_entity_name = True
    _attr_translation_key = "specific_price"

    def __init__(self, coordinator: PriceCoordinator, entry: ConfigEntry, key: str, color: str | None = None):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._key = key  # "HP" or "HC"
        self._color = color.lower() if color else None  # "blue", "white", "red" or None

        slug_parts = [key.lower()]
        if self._color:
            slug_parts.append(self._color)

        self._attr_unique_id = f"{entry.entry_id}_{'_'.join(slug_parts)}"
        self._attr_device_info = child_device_info(entry, CHILD_PRICES)

    @property
    def translation_placeholders(self) -> dict[str, Any]:
        """Return translation placeholders."""
        language = self.hass.config.language if self.hass else "en"
        color_label = localized_color_label(self._color, language) if self._color else ""
        return {
            "period": self._key,
            "color": color_label,
        }


    @property
    def native_value(self) -> float | None:
        """Return the specific price."""
        if not self.coordinator.data:
            return None
            
        prices = self.coordinator.data.get("contract_prices", {})
        
        if self._color:
            # Tempo structure: {"blue": {"HP": x, "HC": y}, ...}
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
        
        # Fixed icon color for specific sensors
        color_key = normalize_color(self._color)
        attributes["icon_color"] = get_icon_color(self.entry.options, color_key)
        
        current_period = data.get("current_period")
        contract = data.get("contract")

        if self._color:
            # Tempo
            current_color = normalize_color(data.get("tempo_color", ""))
            if current_color == self._color and current_period == self._key:
                attributes["active"] = True
        else:
            # Base or HC
            if contract == CONTRACT_BASE:
                attributes["active"] = True
            elif current_period == self._key:
                attributes["active"] = True
                
        return attributes
