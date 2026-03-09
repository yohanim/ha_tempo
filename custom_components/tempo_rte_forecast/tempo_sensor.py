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

    _attr_has_entity_name = True

    def __init__(self, coordinator: TempoDataCoordinator, index: int, entry: ConfigEntry) -> None:
        """Initialisation du sensor."""
        super().__init__(coordinator)

        self.index = index
        self.tempo_day_change_time_str = entry.options.get(CONF_TEMPO_DAY_CHANGE_TIME, TEMPO_DAY_CHANGE_TIME)
        self._attr_unique_id = f"{entry.entry_id}_J{'' if (index == 0) else '+1'}"
        self._last_state = None

        # J (index 0) utilise tempo_color (calendar-today)
        # J+1 (index 1) utilise tempo_forecast (calendar)
        self._attr_translation_key = "tempo_color" if index == 0 else "tempo_forecast"

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
        return {"day": "" if self.index == 0 else " +1"}

    @property
    def available(self) -> bool:
        """Le sensor est disponible si on a au moins des données en cache."""
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
        
        state = day_data.lower() if day_data and day_data.lower() in COLORS else "unknown"

        if state != self._last_state and self._last_state is not None:
            _LOGGER.info("Changement d'état: %s → %s", self._last_state, state)
        
        self._last_state = state
        return state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Attributs détaillés de l'entité."""
        day = get_tempo_date(self.index, self.tempo_day_change_time_str)
        day_data = self.coordinator.get_data(day)
        
        color_key = day_data.lower() if day_data and day_data.lower() in COLORS else "unknown"
        
        day_color_code = COLORS[color_key]["code"]
        day_color = COLORS[color_key]["name"]
        day_color_en = COLORS[color_key]["name_en"]
        day_color_emoji = COLORS[color_key]["emoji"]
        
        if day_data is None:
            data_source = "none"
        elif day in self.coordinator.tempo_data:
            data_source = "api"
        else:
            data_source = "cache"

        return {
            "date": day,
            "color": day_color,
            "color_en": day_color_en,
            "color_code": day_color_code,
            "color_emoji": day_color_emoji,
            "is_blue": color_key == "blue",
            "is_white": color_key == "white",
            "is_red": color_key == "red",
            "data_source": data_source,
        }

class TempoNextDayCombinedSensor(CoordinatorEntity, SensorEntity):
    """Sensor combinant RTE J+1 et OpenDPE si inconnu."""

    _attr_has_entity_name = True
    _attr_translation_key = "tempo_combined"

    def __init__(self, tempo_coordinator: TempoDataCoordinator, forecast_coordinator: ForecastCoordinator, entry: ConfigEntry) -> None:
        """Initialisation."""
        super().__init__(tempo_coordinator)
        self.forecast_coordinator = forecast_coordinator
        self.tempo_day_change_time_str = entry.options.get(CONF_TEMPO_DAY_CHANGE_TIME, TEMPO_DAY_CHANGE_TIME)
        
        self._attr_unique_id = f"{entry.entry_id}_J1_combined"

    @property
    def translation_placeholders(self) -> dict[str, Any]:
        """Return translation placeholders."""
        return {"day": " +1 (Combined)"}

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
        rte_key = rte_data.lower() if rte_data and rte_data.lower() in COLORS else "unknown"

        # Si RTE est connu, on renvoie juste la clé pour la traduction
        if rte_key != "unknown":
            return rte_key

        # Si RTE est inconnu, on construit la chaîne visuelle "❓ + prévision"
        forecast_data = self.forecast_coordinator.get_data(day)
        if forecast_data and forecast_data.color:
            color_key = forecast_data.color.lower()
            forecast_emoji = COLORS.get(color_key, {}).get("emoji", color_key)
            return f"{COLORS['unknown']['emoji']} {forecast_emoji}"

        return rte_key

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Attributs pour le capteur combiné."""
        day = get_tempo_date(1, self.tempo_day_change_time_str)
        rte_data = self.coordinator.get_data(day)
        forecast_data = self.forecast_coordinator.get_data(day)

        rte_key = rte_data.lower() if rte_data and rte_data.lower() in COLORS else "unknown"
        forecast_key = forecast_data.color.lower() if forecast_data else "unknown"
        forecast_emoji = COLORS.get(forecast_key, {}).get("emoji", forecast_key) if forecast_data else "❓"

        # On prépare un objet riche avec les deux sources
        return {
            "date": day,
            "rte_status": COLORS[rte_key]["name"],
            "rte_emoji": COLORS[rte_key]["emoji"],
            "forecast_status": COLORS.get(forecast_key, {}).get("name", forecast_key),
            "forecast_emoji": forecast_emoji,
            "active_source": "RTE" if rte_key != "unknown" else "OpenDPE",
            "color_emoji": COLORS[rte_key]["emoji"] if rte_key != "unknown" else f"{COLORS['unknown']['emoji']} {forecast_emoji}"
        }