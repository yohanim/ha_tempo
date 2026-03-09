"""
EDF Tempo integration for Home Assistant
"""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import CONF_CONTRACT

# Importing coordinator and sensor for tempo validated data
from .tempo_coordinator import TempoDataCoordinator
from .tempo_sensor import TempoSensor, TempoNextDayCombinedSensor

# Importing coordinator and sensors for forecast data
from .forecast_coordinator import ForecastCoordinator
from .forecast_sensor import OpenDPEForecastSensor

# Importing coordinator and sensor for prices data
from .prices_coordinator import PriceCoordinator
from .prices_sensor import PriceSensor, SpecificPriceSensor


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup entities from a config entry."""
    coordinator = TempoDataCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([TempoSensor(coordinator, 0, entry), TempoSensor(coordinator, 1, entry)])

    # Add forecast sensors from Open DPE
    forecast_coordinator = ForecastCoordinator(hass, entry)
    await forecast_coordinator.async_config_entry_first_refresh()
    
    NUM_FORECAST_DAYS = 9  # J+1 to J+9

    sensors = [TempoNextDayCombinedSensor(coordinator, forecast_coordinator, entry)]
    
    for index in range(0, NUM_FORECAST_DAYS):
        sensors.append(OpenDPEForecastSensor(forecast_coordinator, index, entry=entry))
        
    async_add_entities(sensors, True)

    # Add prices sensor
    price_coordinator = PriceCoordinator(hass, entry, coordinator)
    await price_coordinator.async_config_entry_first_refresh()
    
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
