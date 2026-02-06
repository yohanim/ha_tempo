from __future__ import annotations

import logging
import datetime
from typing import List

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator #, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change, async_call_later
from babel.dates import format_date

from .sensor_types import ForecastDayLight, ForecastSensor
from .const import (
    OPEN_DPE_URL,
    RETRY_DELAY_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

class ForecastCoordinator(DataUpdateCoordinator):
    """Coordinator in charge of fetching Open-DPE forecasts."""

    def __init__(self, hass: HomeAssistant):
        """Initializing the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Tempo Forecast Coordinator",
            update_interval=None,  # refresh none as provider do it at fixed hours
        )

        self.hass = hass
        self.session = async_get_clientsession(hass)
        self.tempo_data = {}
        self._cached_data = {}  # Cache pour garder les dernières données valides

        # Daily update after 7h00 and 15h00 with auto-retry and cache
        async_track_time_change(
            hass,
            self._scheduled_refresh,
            hour=7,
            minute=0,
            second=0,
        )
        async_track_time_change(
            hass,
            self._scheduled_refresh,
            hour=15,
            minute=0,
            second=0,
        )

        _LOGGER.debug(
            "ForecastCoordinator initialisé : refresh quotidien programmé à 07:00 + intervalle 6h"
        )

    async def _scheduled_refresh(self, now):
        """Update at 07:00 every day."""
        _LOGGER.debug("Open DPE: lancement du refresh programmé à %sh")
        await self.async_request_refresh()

    async def _async_update_data(self):
        """Open DPE data recovery."""
        try:
            forecasts = await async_fetch_opendpe_forecast(self)
            _LOGGER.debug("Open DPE: %s jours récupérés", len(forecasts))
            return forecasts

        except Exception as exc:
            _LOGGER.error("Open DPE: erreur lors de la mise à jour: %s", exc)
            # raise UpdateFailed(f"Erreur mise à jour des prévisions Open DPE: {exc}")
            async_call_later(self.hass, datetime.timedelta(minutes=RETRY_DELAY_MINUTES), self.async_request_refresh)
        
    def get_data(self, date):
        if date in self.tempo_data:
            return self.tempo_data.get(date)
        return self._cached_data.get(date)


#   Add formated day of week and short date to data
def _format_all_dates(self, data, lang) -> dict[str, ForecastSensor]:
    # Cette fonction s'exécutera dans un thread séparé
    forecasts = {}
    for f_date in data:
        try:
            forecast_date = datetime.datetime.strptime(
                    f_date["date"], "%Y-%m-%d"
                ).date()
            sensor_item = ForecastSensor(
                date        = forecast_date,
                short_date  = format_date(forecast_date, "d LLL", locale=lang),
                day         = format_date(forecast_date, "EEE", locale=lang),
                color       = f_date.get("couleur", "").lower(),
                probability = f_date.get("probability", None)
                )
            forecasts[forecast_date] = sensor_item
            self._cached_data[forecast_date] = sensor_item
        except Exception as exc:
            _LOGGER.warning("Open DPE: ligne ignorée (%s) : %s", exc, f_date)
            continue
    return forecasts

#   Main function (Open-DPE)
async def async_fetch_opendpe_forecast(self):
    """Fetch Tempo forecasts from the Open DPE JSON."""
    session = self.session
    hass = self.hass
    try:
        async with session.get(OPEN_DPE_URL, timeout=10) as response:
            if response.status != 200:
                _LOGGER.error("Open-DPE: HTTP %s", response.status)
                async_call_later(self.hass, datetime.timedelta(minutes=RETRY_DELAY_MINUTES), self.async_request_refresh)
                return self._cached_data

            # Lire le contenu brut pour diagnostic
            response_text = await response.text()
            _LOGGER.debug("[API] Réponse brute (500 premiers chars): %s", response_text[:500])
            response_json = await response.json()
            data = response_json

    except Exception as exc:
        _LOGGER.error("Open DPE: erreur lors de la récupération JSON : %s", exc)
        async_call_later(self.hass, datetime.timedelta(minutes=RETRY_DELAY_MINUTES), self.async_request_refresh)
        return self._cached_data

    forecasts = await hass.async_add_executor_job(_format_all_dates, self, data, hass.config.language)

    return forecasts