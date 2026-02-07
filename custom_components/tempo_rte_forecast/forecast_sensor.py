from __future__ import annotations

from typing import Any, Optional
from dataclasses import asdict
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
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
    CONF_TEMPO_DAY_CHANGE_HOUR,
    TEMPO_DAY_CHANGE_HOUR,
)

from .forecast_coordinator import ForecastCoordinator
# from .sensor_types import ForecastSensor


# -------- Helper functions (copied from sensor.py of RTE Tempo) ----------------
# def get_color_emoji(value: str) -> str:
#     if value == "rouge":
#         return SENSOR_COLOR_RED_EMOJI
#     if value == "blanc":
#         return SENSOR_COLOR_WHITE_EMOJI
#     if value == "bleu":
#         return SENSOR_COLOR_BLUE_EMOJI
#     return SENSOR_COLOR_UNKNOWN_EMOJI


# def get_color_name(value: str) -> str:
#     if value == "rouge":
#         return SENSOR_COLOR_RED_NAME
#     if value == "blanc":
#         return SENSOR_COLOR_WHITE_NAME
#     if value == "bleu":
#         return SENSOR_COLOR_BLUE_NAME
#     return SENSOR_COLOR_UNKNOWN_NAME




# ---------------- Forecast Sensor ----------------------


class OpenDPEForecastSensor(CoordinatorEntity, SensorEntity):
    """OpenDPE forecast sensor (text or visual version)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_has_entity_name = True

    def __init__(self, coordinator: ForecastCoordinator, index: int, visual: bool, entry: ConfigEntry):
        super().__init__(coordinator)

        self.index = index + 1
        self.visual = visual
        self.tempo_day_change_hour = entry.options.get(CONF_TEMPO_DAY_CHANGE_HOUR, TEMPO_DAY_CHANGE_HOUR)

        # ----- Sensor naming and options -----
        if visual:
            self._attr_name = f"OpenDPE J{self.index} (visuel)"
            self._attr_unique_id = f"{DOMAIN}_forecast_opendpe_j{self.index}_emoji"
            self._attr_options = [
                COLORS["BLUE"]["emoji"],
                COLORS["WHITE"]["emoji"],
                COLORS["RED"]["emoji"],
                COLORS["inconnu"]["emoji"],
            ]
            self._attr_icon = "mdi:palette"

        else:
            self._attr_name = f"OpenDPE J{self.index}"
            self._attr_unique_id = f"{DOMAIN}_forecast_opendpe_j{self.index}"
            self._attr_options = [
                COLORS["BLUE"]["name"],
                COLORS["WHITE"]["name"],
                COLORS["RED"]["name"],
                COLORS["inconnu"]["name"],
            ]
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
        day = get_tempo_date(self.index, self.tempo_day_change_hour)
        day_data = self.coordinator.get_data(day)
        return day_data != None

    # ---------------- Native Value ----------------------

    @property
    def native_value(self) -> str | None:
        """Retourne l'état actuel (couleur du jour actuel)."""
        day = get_tempo_date(self.index, self.tempo_day_change_hour)
        day_data = self.coordinator.get_data(day)
        if self.visual:
            return get_color_emoji(day_data.color)
        return get_color_name(day_data.color)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Attributs détaillés de l'entité."""
        day = get_tempo_date(self.index, self.tempo_day_change_hour)
        day_data = self.coordinator.get_data(day)
        return asdict(day_data)

    # ---------------- Coordinator update handler ----------------------

    # def _handle_coordinator_update(self) -> None:
    #     data = self.coordinator.data

    #     if not data or len(data) <= self.index:
    #         self._attr_native_value = None
    #         self._attr_extra_state_attributes = {}
    #         self.async_write_ha_state()
    #         return

    #     forecast: ForecastSensor = data[self.index]
    #     color = forecast.color.lower()

    #     if color not in ["bleu", "blanc", "rouge"]:
    #         color = "inconnu"

    #     # ----- VISUAL VERSION -----
    #     if self.visual:
    #         self._attr_native_value = get_color_emoji(color)
    #         self._attr_icon = get_color_icon(color)

    #     # ----- TEXT VERSION -----
    #     else:
    #         self._attr_native_value = get_color_name(color)

    #     # Extra attributes for both sensors
    #     lang = self.hass.config.language
    #     self._attr_extra_state_attributes = {
    #         "day": forecast.day,
    #         "short_date": forecast.short_date,
    #         "date": forecast.date.isoformat(),
    #         "probability": forecast.probability,
    #         "attribution": "Données Tempo : Open DPE (https://open-dpe.fr)",
    #     }

    #     self.async_write_ha_state()