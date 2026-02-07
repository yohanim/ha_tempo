"""
Integration Home Assistant pour EDF Tempo
Une seule entité sensor avec tous les états et attributs
Version robuste avec gestion des données instables

Copyright (C) 2025 Christophe Bansart

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

# Importing coordinator and sensor for tempo validated data
from .tempo_coordinator import TempoDataCoordinator
from .tempo_sensor import TempoSensor

# Importing coordinator and sensors for forecast data
from .forecast_coordinator import ForecastCoordinator
from .forecast_sensor import OpenDPEForecastSensor


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configuration de l'entité depuis une config entry."""
    coordinator = TempoDataCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([TempoSensor(coordinator, 0, entry), TempoSensor(coordinator, 1, entry)])

    #   Add forecast sensors from Open DPE
    forecast_coordinator = ForecastCoordinator(hass, entry)
    await forecast_coordinator.async_config_entry_first_refresh()
    
    NUM_FORECAST_DAYS = 9  # J+1 à J+9

    sensors = []
    
    # Skip index 0 (J+1) because RTE provides the official J+1 sensor
    for index in range(1, NUM_FORECAST_DAYS):
        # Text version
        sensors.append(OpenDPEForecastSensor(forecast_coordinator, index, visual=False, entry=entry))
        # Visual version (emoji)
        sensors.append(OpenDPEForecastSensor(forecast_coordinator, index, visual=True, entry=entry))
        
    async_add_entities(sensors, True)
