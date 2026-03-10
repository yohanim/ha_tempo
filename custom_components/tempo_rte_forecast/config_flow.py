"""
Config flow for EDF Tempo integration
Copyright (C) 2025 Christophe Bansart
"""
from __future__ import annotations

import logging
from typing import Any
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    OptionsFlowWithReload,
    ConfigEntry,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    DEVICE_NAME,
    TEMPO_RETRY_DELAY_MINUTES,
    FORECAST_RETRY_DELAY_MINUTES,
    CONF_TEMPO_DAY_CHANGE_TIME,
    TEMPO_DAY_CHANGE_TIME,
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

_LOGGER = logging.getLogger(__name__)

class TempoConfigFlow(ConfigFlow, domain=DOMAIN):
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
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler()

class OptionsFlowHandler(OptionsFlowWithReload):
    """Handle options flow using modern Reload pattern."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opts = self.config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_CONTRACT): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["Base", "Heures Creuses", "Tempo"],
                        translation_key="contract",
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_SUBSCRIBED_POWER): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=['3', '6', '9', '12', '15', '18', '24', '30', '36'],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_OFFPEAK_RANGES): selector.TextSelector(),
                vol.Optional(CONF_PRICE_UPDATE_INTERVAL): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=30, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(CONF_OPENDPE_SERVICE_TYPE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[OPENDPE_SERVICE_LIGHT, OPENDPE_SERVICE_FULL],
                        translation_key="opendpe_service_type",
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_TEMPO_DAY_CHANGE_TIME): selector.TimeSelector(),
                vol.Optional(CONF_RTE_TEMPO_COLOR_REFRESH_TIME): selector.TimeSelector(),
                vol.Optional(CONF_EDF_TEMPO_COLOR_REFRESH_TIME): selector.TimeSelector(),
                vol.Optional(CONF_TEMPO_RETRY_DELAY): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=1440, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_FORECAST_RETRY_DELAY): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=1440, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_ICON_COLOR_BLUE): selector.TextSelector(),
                vol.Optional(CONF_ICON_COLOR_WHITE): selector.TextSelector(),
                vol.Optional(CONF_ICON_COLOR_RED): selector.TextSelector(),
                vol.Optional(CONF_ICON_COLOR_UNKNOWN): selector.TextSelector(),
            }),
            suggested_values={
                CONF_CONTRACT: opts.get(CONF_CONTRACT, "Tempo"),
                CONF_SUBSCRIBED_POWER: opts.get(CONF_SUBSCRIBED_POWER, DEFAULT_SUBSCRIBED_POWER),
                CONF_OFFPEAK_RANGES: opts.get(CONF_OFFPEAK_RANGES, DEFAULT_OFFPEAK_RANGES),
                CONF_PRICE_UPDATE_INTERVAL: opts.get(CONF_PRICE_UPDATE_INTERVAL, DEFAULT_PRICE_UPDATE_INTERVAL),
                CONF_OPENDPE_SERVICE_TYPE: opts.get(CONF_OPENDPE_SERVICE_TYPE, OPENDPE_SERVICE_LIGHT),
                CONF_TEMPO_DAY_CHANGE_TIME: opts.get(CONF_TEMPO_DAY_CHANGE_TIME, TEMPO_DAY_CHANGE_TIME),
                CONF_RTE_TEMPO_COLOR_REFRESH_TIME: opts.get(CONF_RTE_TEMPO_COLOR_REFRESH_TIME, DEFAULT_RTE_TEMPO_COLOR_REFRESH_TIME),
                CONF_EDF_TEMPO_COLOR_REFRESH_TIME: opts.get(CONF_EDF_TEMPO_COLOR_REFRESH_TIME, DEFAULT_EDF_TEMPO_COLOR_REFRESH_TIME),
                CONF_TEMPO_RETRY_DELAY: opts.get(CONF_TEMPO_RETRY_DELAY, TEMPO_RETRY_DELAY_MINUTES),
                CONF_FORECAST_RETRY_DELAY: opts.get(CONF_FORECAST_RETRY_DELAY, FORECAST_RETRY_DELAY_MINUTES),
                CONF_ICON_COLOR_BLUE: opts.get(CONF_ICON_COLOR_BLUE, DEFAULT_ICON_COLOR_BLUE),
                CONF_ICON_COLOR_WHITE: opts.get(CONF_ICON_COLOR_WHITE, DEFAULT_ICON_COLOR_WHITE),
                CONF_ICON_COLOR_RED: opts.get(CONF_ICON_COLOR_RED, DEFAULT_ICON_COLOR_RED),
                CONF_ICON_COLOR_UNKNOWN: opts.get(CONF_ICON_COLOR_UNKNOWN, DEFAULT_ICON_COLOR_UNKNOWN),
            }
        )
