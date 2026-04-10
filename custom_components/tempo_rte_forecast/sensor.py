"""
EDF Tempo integration for Home Assistant
"""
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TempoConfigEntry
from .const import CONF_CONTRACT

from .tempo_sensor import TempoSensor, TempoNextDayCombinedSensor

from .forecast_sensor import OpenDPEForecastSensor

from .prices_sensor import PriceSensor, SpecificPriceSensor


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TempoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup entities from a config entry."""
    coordinator = entry.runtime_data.tempo_coordinator
    forecast_coordinator = entry.runtime_data.forecast_coordinator
    price_coordinator = entry.runtime_data.price_coordinator

    async_add_entities(
        [
            TempoSensor(
                coordinator,
                0,
                entry,
                forecast_coordinator=forecast_coordinator,
            ),
            TempoSensor(
                coordinator,
                1,
                entry,
                forecast_coordinator=forecast_coordinator,
            ),
        ]
    )

    # Add forecast sensors from Open DPE
    NUM_FORECAST_DAYS = 9  # J+1 to J+9

    sensors = [TempoNextDayCombinedSensor(coordinator, forecast_coordinator, entry)]
    
    for index in range(0, NUM_FORECAST_DAYS):
        sensors.append(OpenDPEForecastSensor(forecast_coordinator, index, entry=entry))

    async_add_entities(sensors, True)

    # Add prices sensor
    price_sensors = [PriceSensor(price_coordinator, entry)]

    # Add specific sensors based on contract type
    contract = entry.options.get(CONF_CONTRACT, "Tempo")

    if contract == "Base":
        price_sensors.append(SpecificPriceSensor(price_coordinator, entry, key="HP"))
    elif contract == "Heures Creuses":
        price_sensors.append(SpecificPriceSensor(price_coordinator, entry, key="HP"))
        price_sensors.append(SpecificPriceSensor(price_coordinator, entry, key="HC"))
    elif contract == "Tempo":
        for color in ["blue", "white", "red"]:
            price_sensors.append(SpecificPriceSensor(price_coordinator, entry, key="HP", color=color))
            price_sensors.append(SpecificPriceSensor(price_coordinator, entry, key="HC", color=color))

    async_add_entities(price_sensors)
