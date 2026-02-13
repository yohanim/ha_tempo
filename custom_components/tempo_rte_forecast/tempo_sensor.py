from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
import logging
from typing import Any, Optional

from .tempo_coordinator import TempoDataCoordinator
from .forecast_coordinator import ForecastCoordinator
from .utils import get_tempo_date, get_color_code, get_color_name, get_color_emoji, get_color_name_en
from .const import (
    DOMAIN,
    DEVICE_NAME,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    COLORS,
    CONF_TEMPO_DAY_CHANGE_TIME,
    TEMPO_DAY_CHANGE_TIME,
)

_LOGGER = logging.getLogger(__name__)

class TempoSensor(CoordinatorEntity, SensorEntity):
    """Sensor principal représentant l'état Tempo."""

    def __init__(self, coordinator: TempoDataCoordinator, index: int, entry: ConfigEntry) -> None:
        """Initialisation du sensor."""
        super().__init__(coordinator)

        self.index = index
        self.tempo_day_change_time_str = entry.options.get(CONF_TEMPO_DAY_CHANGE_TIME, TEMPO_DAY_CHANGE_TIME)
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
        # Pour le capteur J+1, on le veut toujours disponible pour afficher "Inconnu".
        if self.index == 1:
            return True

        day = get_tempo_date(self.index, self.tempo_day_change_time_str)
        day_data = self.coordinator.get_data(day)
        return day_data is not None

    @property
    def native_value(self) -> str:
        """Retourne l'état actuel (couleur du jour actuel)."""
        day = get_tempo_date(self.index, self.tempo_day_change_time_str)
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
        day = get_tempo_date(self.index, self.tempo_day_change_time_str)
        day_data = self.coordinator.get_data(day)
        
        day_color_code = get_color_code(day_data)
        day_color = get_color_name(day_data)
        day_color_en = get_color_name_en(day_data)
        day_color_emoji = get_color_emoji(day_data)
        
        if day_data is None:
            data_source = "none"
        elif day in self.coordinator.tempo_data:
            data_source = "api"
        else:
            data_source = "cache"

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
            "data_source": data_source,
        }

class TempoNextDayCombinedSensor(CoordinatorEntity, SensorEntity):
    """Sensor combinant RTE J+1 et OpenDPE si inconnu."""

    def __init__(self, tempo_coordinator: TempoDataCoordinator, forecast_coordinator: ForecastCoordinator, entry: ConfigEntry) -> None:
        """Initialisation."""
        super().__init__(tempo_coordinator)
        self.forecast_coordinator = forecast_coordinator
        self.tempo_day_change_time_str = entry.options.get(CONF_TEMPO_DAY_CHANGE_TIME, TEMPO_DAY_CHANGE_TIME)
        
        self._attr_name = "Tempo J+1 (Synthèse)"
        self._attr_unique_id = f"{DOMAIN}_J1_combined"
        self._attr_icon = "mdi:calendar-end"
        self._attr_has_entity_name = True

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        await super().async_added_to_hass()
        # Also listen to forecast updates
        self.async_on_remove(
            self.forecast_coordinator.async_add_listener(
                self._handle_coordinator_update
            )
        )

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "forecast")},
            name=DEVICE_NAME,
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
        )

    @property
    def native_value(self) -> str:
        day = get_tempo_date(1, self.tempo_day_change_time_str)
        
        # RTE Data
        rte_data = self.coordinator.get_data(day)
        rte_emoji = get_color_emoji(rte_data)
        
        # Si RTE est inconnu, on regarde la prévision
        if rte_emoji == COLORS["inconnu"]["emoji"]:
            forecast_data = self.forecast_coordinator.get_data(day)
            if forecast_data and forecast_data.color:
                # Si la couleur est dans COLORS, on prend l'emoji, sinon c'est déjà un emoji (probabilités)
                if forecast_data.color in COLORS:
                    forecast_emoji = get_color_emoji(forecast_data.color)
                else:
                    forecast_emoji = forecast_data.color
                
                return f"{rte_emoji} {forecast_emoji}"
        
        return rte_emoji