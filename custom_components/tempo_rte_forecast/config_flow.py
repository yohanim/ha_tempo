"""
Config flow for EDF Tempo integration
Copyright (C) 2025 Christophe Bansart
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
    CONF_OPENDPE_SERVICE_TYPE,
    OPENDPE_SERVICE_LIGHT,
    OPENDPE_SERVICE_FULL,
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
    CONF_ICON_COLOR_BLUE,
    CONF_ICON_COLOR_WHITE,
    CONF_ICON_COLOR_RED,
    CONF_ICON_COLOR_UNKNOWN,
    DEFAULT_ICON_COLOR_BLUE,
    DEFAULT_ICON_COLOR_WHITE,
    DEFAULT_ICON_COLOR_RED,
    DEFAULT_ICON_COLOR_UNKNOWN,
)


class TempoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Tempo."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Initial setup step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
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
    """Handle options flow."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_CONTRACT,
                    default=options.get(CONF_CONTRACT, "Tempo")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["Base", "Heures Creuses", "Tempo"],
                        translation_key="contract",
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_SUBSCRIBED_POWER,
                    default=options.get(CONF_SUBSCRIBED_POWER, DEFAULT_SUBSCRIBED_POWER)
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=['3', '6', '9', '12', '15', '18', '24', '30', '36'],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_OFFPEAK_RANGES,
                    default=options.get(CONF_OFFPEAK_RANGES, DEFAULT_OFFPEAK_RANGES)
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_PRICE_UPDATE_INTERVAL,
                    default=options.get(CONF_PRICE_UPDATE_INTERVAL, DEFAULT_PRICE_UPDATE_INTERVAL)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=30,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_OPENDPE_SERVICE_TYPE,
                    default=options.get(CONF_OPENDPE_SERVICE_TYPE, OPENDPE_SERVICE_LIGHT)
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[OPENDPE_SERVICE_LIGHT, OPENDPE_SERVICE_FULL],
                        translation_key="opendpe_service_type",
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_TEMPO_DAY_CHANGE_TIME, 
                    default=options.get(CONF_TEMPO_DAY_CHANGE_TIME, TEMPO_DAY_CHANGE_TIME)
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_RTE_TEMPO_COLOR_REFRESH_TIME,
                    default=options.get(CONF_RTE_TEMPO_COLOR_REFRESH_TIME, DEFAULT_RTE_TEMPO_COLOR_REFRESH_TIME)
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_EDF_TEMPO_COLOR_REFRESH_TIME,
                    default=options.get(CONF_EDF_TEMPO_COLOR_REFRESH_TIME, DEFAULT_EDF_TEMPO_COLOR_REFRESH_TIME)
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_TEMPO_RETRY_DELAY, 
                    default=options.get(CONF_TEMPO_RETRY_DELAY, TEMPO_RETRY_DELAY_MINUTES)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=1440, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(
                    CONF_FORECAST_RETRY_DELAY, 
                    default=options.get(CONF_FORECAST_RETRY_DELAY, FORECAST_RETRY_DELAY_MINUTES)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=1440, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(
                    CONF_ICON_COLOR_BLUE,
                    default=options.get(CONF_ICON_COLOR_BLUE, DEFAULT_ICON_COLOR_BLUE)
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_ICON_COLOR_WHITE,
                    default=options.get(CONF_ICON_COLOR_WHITE, DEFAULT_ICON_COLOR_WHITE)
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_ICON_COLOR_RED,
                    default=options.get(CONF_ICON_COLOR_RED, DEFAULT_ICON_COLOR_RED)
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_ICON_COLOR_UNKNOWN,
                    default=options.get(CONF_ICON_COLOR_UNKNOWN, DEFAULT_ICON_COLOR_UNKNOWN)
                ): selector.TextSelector(),
            }),
        )
