"""
Config flow for EDF Tempo integration
Copyright (C) 2025 Christophe Bansart
"""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    OptionsFlow,
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

class OptionsFlowHandler(OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._data: dict[str, Any] = dict(config_entry.options)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["prices", "api", "retries", "icons", "finish"]
        )

    async def async_step_prices(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage price settings."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_init()

        return self.async_show_form(
            step_id="prices",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({
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
                }),
                {
                    CONF_CONTRACT: self._data.get(CONF_CONTRACT, "Tempo"),
                    CONF_SUBSCRIBED_POWER: self._data.get(CONF_SUBSCRIBED_POWER, DEFAULT_SUBSCRIBED_POWER),
                    CONF_OFFPEAK_RANGES: self._data.get(CONF_OFFPEAK_RANGES, DEFAULT_OFFPEAK_RANGES),
                    CONF_PRICE_UPDATE_INTERVAL: int(self._data.get(CONF_PRICE_UPDATE_INTERVAL) or DEFAULT_PRICE_UPDATE_INTERVAL),
                }
            ),
        )

    async def async_step_api(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage API settings."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_init()

        return self.async_show_form(
            step_id="api",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({
                    vol.Optional(CONF_TEMPO_DAY_CHANGE_TIME): selector.TimeSelector(),
                    vol.Optional(CONF_RTE_TEMPO_COLOR_REFRESH_TIME): selector.TimeSelector(),
                    vol.Optional(CONF_EDF_TEMPO_COLOR_REFRESH_TIME): selector.TimeSelector(),
                    vol.Optional(CONF_OPENDPE_SERVICE_TYPE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[OPENDPE_SERVICE_LIGHT, OPENDPE_SERVICE_FULL],
                            translation_key="opendpe_service_type",
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }),
                {
                    CONF_TEMPO_DAY_CHANGE_TIME: self._data.get(CONF_TEMPO_DAY_CHANGE_TIME, TEMPO_DAY_CHANGE_TIME),
                    CONF_RTE_TEMPO_COLOR_REFRESH_TIME: self._data.get(CONF_RTE_TEMPO_COLOR_REFRESH_TIME) or self._data.get("api_refresh_time") or DEFAULT_RTE_TEMPO_COLOR_REFRESH_TIME,
                    CONF_EDF_TEMPO_COLOR_REFRESH_TIME: self._data.get(CONF_EDF_TEMPO_COLOR_REFRESH_TIME, DEFAULT_EDF_TEMPO_COLOR_REFRESH_TIME),
                    CONF_OPENDPE_SERVICE_TYPE: self._data.get(CONF_OPENDPE_SERVICE_TYPE, OPENDPE_SERVICE_LIGHT),
                }
            ),
        )

    async def async_step_retries(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage retry settings."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_init()

        return self.async_show_form(
            step_id="retries",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({
                    vol.Optional(CONF_TEMPO_RETRY_DELAY): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=1, max=1440, mode=selector.NumberSelectorMode.BOX)
                    ),
                    vol.Optional(CONF_FORECAST_RETRY_DELAY): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=1, max=1440, mode=selector.NumberSelectorMode.BOX)
                    ),
                }),
                {
                    CONF_TEMPO_RETRY_DELAY: int(self._data.get(CONF_TEMPO_RETRY_DELAY) or TEMPO_RETRY_DELAY_MINUTES),
                    CONF_FORECAST_RETRY_DELAY: int(self._data.get(CONF_FORECAST_RETRY_DELAY) or FORECAST_RETRY_DELAY_MINUTES),
                }
            ),
        )

    async def async_step_icons(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage icon settings."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_init()

        return self.async_show_form(
            step_id="icons",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({
                    vol.Optional(CONF_ICON_COLOR_BLUE): selector.TextSelector(),
                    vol.Optional(CONF_ICON_COLOR_WHITE): selector.TextSelector(),
                    vol.Optional(CONF_ICON_COLOR_RED): selector.TextSelector(),
                    vol.Optional(CONF_ICON_COLOR_UNKNOWN): selector.TextSelector(),
                }),
                {
                    CONF_ICON_COLOR_BLUE: self._data.get(CONF_ICON_COLOR_BLUE, DEFAULT_ICON_COLOR_BLUE),
                    CONF_ICON_COLOR_WHITE: self._data.get(CONF_ICON_COLOR_WHITE, DEFAULT_ICON_COLOR_WHITE),
                    CONF_ICON_COLOR_RED: self._data.get(CONF_ICON_COLOR_RED, DEFAULT_ICON_COLOR_RED),
                    CONF_ICON_COLOR_UNKNOWN: self._data.get(CONF_ICON_COLOR_UNKNOWN, DEFAULT_ICON_COLOR_UNKNOWN),
                }
            ),
        )

    async def async_step_finish(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Finish the options flow."""
        return self.async_create_entry(title="", data=self._data)

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

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=DEVICE_NAME, data={})


    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)
