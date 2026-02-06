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
import voluptuous as vol
from homeassistant import config_entries
# from homeassistant.data_entry_flow import FlowResult
# from homeassistant.core import callback

from .const import (DOMAIN, DEVICE_NAME)


class TempoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow pour Tempo."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
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


#     @staticmethod
#     @callback
#     def async_get_options_flow(
#         config_entry: config_entries.ConfigEntry,
#     ) -> config_entries.OptionsFlow:
#         """Create the options flow."""
#         return OptionsFlowHandler(config_entry.entry_id)

# class OptionsFlowHandler(config_entries.OptionsFlow):
#     def __init__(self, config_entry_id: str) -> None:
#         """Initialize options flow."""
#         self.config_entry_id = config_entry_id

#     async def async_step_init(
#         self, user_input: dict[str, Any] | None = None
#     ) -> FlowResult:
#         """Manage the options."""
#         if user_input is not None:
#             return self.async_create_entry(title="", data=user_input)

#         config_entry = self.hass.config_entries.async_get_entry(self.config_entry_id)

#         default_offpeak_hours = None
#         if config_entry.data['contract_type'] == CONTRACT_TYPE_TEMPO:
#             default_offpeak_hours = TEMPO_OFFPEAK_HOURS

#         return self.async_show_form(
#             step_id="init",
#             data_schema=vol.Schema(
#                 {
#                     vol.Optional("refresh_interval", default=config_entry.options.get("refresh_interval", DEFAULT_REFRESH_INTERVAL)): int,
#                     vol.Optional("off_peak_hours_ranges", default=config_entry.options.get("off_peak_hours_ranges", default_offpeak_hours)): str,
#                 }
#             ),
#         )
