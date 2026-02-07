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

from .const import (
    DOMAIN,
    DEVICE_NAME,
    TEMPO_DAY_CHANGE_HOUR,
    TEMPO_RETRY_DELAY_MINUTES,
    FORECAST_RETRY_DELAY_MINUTES,
    CONF_TEMPO_DAY_CHANGE_HOUR,
    CONF_TEMPO_RETRY_DELAY,
    CONF_FORECAST_RETRY_DELAY,
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
                    "description": "Cette intégration récupère les couleurs Tempo depuis l'API RTE et crée une entité unique avec tous les états."
                },
            )
        
        return self.async_create_entry(title=DEVICE_NAME, data={})


    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_TEMPO_DAY_CHANGE_HOUR, default=self.config_entry.options.get(CONF_TEMPO_DAY_CHANGE_HOUR, TEMPO_DAY_CHANGE_HOUR)): int,
                vol.Optional(CONF_TEMPO_RETRY_DELAY, default=self.config_entry.options.get(CONF_TEMPO_RETRY_DELAY, TEMPO_RETRY_DELAY_MINUTES)): int,
                vol.Optional(CONF_FORECAST_RETRY_DELAY, default=self.config_entry.options.get(CONF_FORECAST_RETRY_DELAY, FORECAST_RETRY_DELAY_MINUTES)): int,
            }),
        )
