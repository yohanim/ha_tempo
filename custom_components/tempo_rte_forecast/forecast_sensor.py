from __future__ import annotations

from typing import Any, Optional
from dataclasses import asdict
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .utils import get_tempo_date, get_color_name, get_color_emoji
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
# from .sensor_types import ForecastSensor

# ---------------- Forecast Sensor ----------------------


class OpenDPEForecastSensor(CoordinatorEntity, SensorEntity):
    """OpenDPE forecast sensor (text or visual version)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ForecastCoordinator, index: int, visual: bool, entry: ConfigEntry):
        super().__init__(coordinator)

        self.index = index + 1
        self.visual = visual
        self.tempo_day_change_time_str = entry.options.get(CONF_TEMPO_DAY_CHANGE_TIME, TEMPO_DAY_CHANGE_TIME)

        # ----- Sensor naming and options -----
        if visual:
            self._attr_name = f"OpenDPE J{self.index} (visuel)"
            self._attr_unique_id = f"{DOMAIN}_forecast_opendpe_j{self.index}_emoji"
            self._attr_icon = "mdi:palette"

        else:
            self._attr_name = f"OpenDPE J{self.index}"
            self._attr_unique_id = f"{DOMAIN}_forecast_opendpe_j{self.index}"
            self._attr_icon = "mdi:calendar"

        # self._attr_native_value = index + 1
        self._attr_native_value: Optional[str] = None
        self._attr_extra_state_attributes = {}

    # ---------------- Device Info ----------------------

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info shared by all forecast sensors."""
        return DeviceInfo(
            identifiers={(DOMAIN, "forecast")},
            name=DEVICE_NAME,
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
        )

    # ---------------- Availability ----------------------

    @property
    def available(self) -> bool:
        """Le sensor est disponible si on a au moins des données en cache."""
        day = get_tempo_date(self.index, self.tempo_day_change_time_str)
        day_data = self.coordinator.get_data(day)
        return day_data != None

    # ---------------- Native Value ----------------------

    @property
    def native_value(self) -> str | None:
        """Retourne l'état actuel (couleur du jour actuel)."""
        day = get_tempo_date(self.index, self.tempo_day_change_time_str)
        day_data = self.coordinator.get_data(day)
        if day_data is None:
            return None
        if day_data.color not in COLORS:
            return day_data.color
        if self.visual:
            return get_color_emoji(day_data.color)
        return get_color_name(day_data.color)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Attributs détaillés de l'entité."""
        day = get_tempo_date(self.index, self.tempo_day_change_time_str)
        day_data = self.coordinator.get_data(day)
        return asdict(day_data)
