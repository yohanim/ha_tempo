from __future__ import annotations

from typing import Any, Optional
from dataclasses import asdict
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .utils import get_tempo_date, get_color_name, get_color_emoji, normalize_color, get_icon_color
from .const import (
    DOMAIN,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    COLORS,
    DEVICE_NAME,
    CONF_TEMPO_DAY_CHANGE_TIME,
    TEMPO_DAY_CHANGE_TIME,
)

from .forecast_coordinator import ForecastCoordinator

class OpenDPEForecastSensor(CoordinatorEntity, SensorEntity):
    """OpenDPE forecast sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "tempo_forecast"

    def __init__(self, coordinator: ForecastCoordinator, index: int, entry: ConfigEntry):
        super().__init__(coordinator)

        self.index = index + 1
        self.tempo_day_change_time_str = entry.options.get(CONF_TEMPO_DAY_CHANGE_TIME, TEMPO_DAY_CHANGE_TIME)
        self._attr_unique_id = f"{entry.entry_id}_forecast_opendpe_j{self.index}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info shared by all forecast sensors."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=DEVICE_NAME,
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
        )

    @property
    def translation_placeholders(self) -> dict[str, Any]:
        """Return translation placeholders."""
        return {"day": str(self.index)}

    @property
    def available(self) -> bool:
        """Sensor is available if data is in cache."""
        day = get_tempo_date(self.index, self.tempo_day_change_time_str)
        day_data = self.coordinator.get_data(day)
        return day_data != None

    @property
    def native_value(self) -> str | None:
        """Return current state."""
        day = get_tempo_date(self.index, self.tempo_day_change_time_str)
        day_data = self.coordinator.get_data(day)
        if day_data is None:
            return None
            
        return normalize_color(day_data.color)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Detailed entity attributes."""
        day = get_tempo_date(self.index, self.tempo_day_change_time_str)
        day_data = self.coordinator.get_data(day)
        if day_data is None:
            return {}
            
        attrs = asdict(day_data)
        color_key = normalize_color(day_data.color)
        attrs["icon_color"] = get_icon_color(self.coordinator.entry.options, color_key)

        if color_key in COLORS:
            attrs["color_name"] = COLORS[color_key]["name"]
            attrs["color_emoji"] = COLORS[color_key]["emoji"]
        else:
            # Probability string case
            attrs["color_name"] = day_data.color
            attrs["color_emoji"] = day_data.color
            
        return attrs
