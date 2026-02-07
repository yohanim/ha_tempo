from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
import logging
from typing import Any, Optional

from .tempo_coordinator import TempoDataCoordinator
from .utils import get_tempo_date, get_color_code, get_color_name, get_color_emoji, get_color_name_en
from .const import (
    DOMAIN,
    DEVICE_NAME,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    CONF_TEMPO_DAY_CHANGE_HOUR,
    TEMPO_DAY_CHANGE_HOUR,
)

_LOGGER = logging.getLogger(__name__)

class TempoSensor(CoordinatorEntity, SensorEntity):
    """Sensor principal représentant l'état Tempo."""

    def __init__(self, coordinator: TempoDataCoordinator, index: int, entry: ConfigEntry) -> None:
        """Initialisation du sensor."""
        super().__init__(coordinator)

        self.index = index
        self.tempo_day_change_hour = entry.options.get(CONF_TEMPO_DAY_CHANGE_HOUR, TEMPO_DAY_CHANGE_HOUR)
        self._attr_name = f"RTE Tempo color J{'' if (index == 0) else '+1'}"
        self._attr_unique_id = f"{DOMAIN}_J{'' if (index == 0) else '+1'}"
        self._attr_icon = "mdi:flash"
        self._attr_has_entity_name = True
        self._last_state = None

        self._attr_native_value: Optional[str] = None

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

    @property
    def available(self) -> bool:
        """Le sensor est disponible si on a au moins des données en cache."""
        day = get_tempo_date(self.index, self.tempo_day_change_hour)
        day_data = self.coordinator.get_data(day)
        return day_data != None

    @property
    def native_value(self) -> str:
        """Retourne l'état actuel (couleur du jour actuel)."""
        day = get_tempo_date(self.index, self.tempo_day_change_hour)
        day_data = self.coordinator.get_data(day)
        day_color_emoji = get_color_emoji(day_data)

        # Log uniquement si l'état change réellement
        if day_color_emoji != self._last_state and self._last_state is not None:
            _LOGGER.info("Changement d'état: %s → %s", self._last_state, day_color_emoji)
        
        self._last_state = day_color_emoji
        return day_color_emoji

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Attributs détaillés de l'entité."""
        day = get_tempo_date(self.index, self.tempo_day_change_hour)
        day_data = self.coordinator.get_data(day)
        
        day_color_code = get_color_code(day_data)
        day_color = get_color_name(day_data)
        day_color_en = get_color_name_en(day_data)
        day_color_emoji = get_color_emoji(day_data)
        
        return {
            # Jour J
            "date": day,
            "color": day_color,
            "color_en": day_color_en,
            "color_code": day_color_code,
            "color_emoji":day_color_emoji,
            "is_blue": day_color_code == 1,
            "is_white": day_color_code == 2,
            "is_red": day_color_code == 3,

            # Info système
            "data_source": "cache" if day not in self.coordinator.tempo_data else "api",
        }