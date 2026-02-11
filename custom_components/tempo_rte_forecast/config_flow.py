"""
Config flow for EDF Tempo integration
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
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback
from homeassistant.config_entries import OptionsFlow
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    DEVICE_NAME,
    TEMPO_DAY_CHANGE_TIME,
    TEMPO_RETRY_DELAY_MINUTES,
    FORECAST_RETRY_DELAY_MINUTES,
    CONF_TEMPO_DAY_CHANGE_TIME,
    CONF_TEMPO_RETRY_DELAY,
    CONF_FORECAST_RETRY_DELAY,
    CONF_RTE_TEMPO_COLOR_REFRESH_TIME,
    DEFAULT_RTE_TEMPO_COLOR_REFRESH_TIME,
    CONF_EDF_TEMPO_COLOR_REFRESH_TIME,
    DEFAULT_EDF_TEMPO_COLOR_REFRESH_TIME,
    CONF_CONTRACT,
    CONF_OFFPEAK_RANGES,
    DEFAULT_OFFPEAK_RANGES,
    CONF_SUBSCRIBED_POWER,
    DEFAULT_SUBSCRIBED_POWER,
    CONF_PRICE_UPDATE_INTERVAL,
    DEFAULT_PRICE_UPDATE_INTERVAL,
)


class TempoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow pour Tempo."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Étape initiale de configuration."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "description": "Cette intégration récupère les couleurs Tempo, les prévisions et les prix de l'électricité."
                },
            )
        
        return self.async_create_entry(title=DEVICE_NAME, data={})


    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler()

class OptionsFlowHandler(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_options = self.config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_CONTRACT,
                    default=current_options.get(CONF_CONTRACT, "Tempo")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["Base", "Heures Creuses", "Tempo"],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_SUBSCRIBED_POWER,
                    default=current_options.get(CONF_SUBSCRIBED_POWER, DEFAULT_SUBSCRIBED_POWER)
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=['3', '6', '9', '12', '15', '18', '24', '30', '36'],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_OFFPEAK_RANGES,
                    default=current_options.get(CONF_OFFPEAK_RANGES, DEFAULT_OFFPEAK_RANGES)
                ): str,
                vol.Optional(
                    CONF_PRICE_UPDATE_INTERVAL,
                    default=current_options.get(CONF_PRICE_UPDATE_INTERVAL, DEFAULT_PRICE_UPDATE_INTERVAL)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=30,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_TEMPO_DAY_CHANGE_TIME, 
                    default=current_options.get(CONF_TEMPO_DAY_CHANGE_TIME, TEMPO_DAY_CHANGE_TIME)
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_RTE_TEMPO_COLOR_REFRESH_TIME,
                    default=current_options.get(CONF_RTE_TEMPO_COLOR_REFRESH_TIME, current_options.get("api_refresh_time", DEFAULT_RTE_TEMPO_COLOR_REFRESH_TIME))
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_EDF_TEMPO_COLOR_REFRESH_TIME,
                    default=current_options.get(CONF_EDF_TEMPO_COLOR_REFRESH_TIME, DEFAULT_EDF_TEMPO_COLOR_REFRESH_TIME)
                ): selector.TimeSelector(),
                vol.Optional(CONF_TEMPO_RETRY_DELAY, default=int(current_options.get(CONF_TEMPO_RETRY_DELAY, TEMPO_RETRY_DELAY_MINUTES))): int,
                vol.Optional(CONF_FORECAST_RETRY_DELAY, default=int(current_options.get(CONF_FORECAST_RETRY_DELAY, FORECAST_RETRY_DELAY_MINUTES))): int,
            }),
        )
