from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
import json

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change, async_call_later
from babel.dates import format_date, get_date_format

from .sensor_types import ForecastSensor, ForecastDayLight, ForecastDay
from .const import (
    OPEN_DPE_LIGHT_URL,
    OPEN_DPE_FULL_URL,
    FORECAST_RETRY_DELAY_MINUTES,
    CONF_FORECAST_RETRY_DELAY,
    CONF_OPENDPE_SERVICE_TYPE,
    OPENDPE_SERVICE_LIGHT,
    OPENDPE_SERVICE_FULL,
    COLORS,
)

_LOGGER = logging.getLogger(__name__)

class ForecastCoordinator(DataUpdateCoordinator):
    """Coordinator in charge of fetching Open-DPE forecasts."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initializing the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Tempo Forecast Coordinator",
            update_interval=None,  # refresh none as provider do it at fixed hours
        )

        self.hass = hass
        self.session = async_get_clientsession(hass)
        self.entry = entry
        self.update_listener = entry.add_update_listener(self._options_update_callback)
        self.retry_delay = entry.options.get(CONF_FORECAST_RETRY_DELAY, FORECAST_RETRY_DELAY_MINUTES)
        self.service_type = entry.options.get(CONF_OPENDPE_SERVICE_TYPE, OPENDPE_SERVICE_LIGHT)
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

    async def _options_update_callback(self, hass: HomeAssistant, entry: ConfigEntry):
        """Handle options update."""
        _LOGGER.info("Configuration options for Tempo Forecast updated, requesting refresh.")
        self.service_type = entry.options.get(CONF_OPENDPE_SERVICE_TYPE, OPENDPE_SERVICE_LIGHT)
        self.retry_delay = entry.options.get(CONF_FORECAST_RETRY_DELAY, FORECAST_RETRY_DELAY_MINUTES)
        await self.async_request_refresh()

    async def _scheduled_refresh(self, now: datetime) -> None:
        """Update at 07:00 every day."""
        _LOGGER.debug("Open DPE: lancement du refresh programmé à %s", now.strftime("%Hh%M"))
        await self.async_refresh()

    async def _async_update_data(self) -> dict[str, ForecastSensor] | None:
        """Open DPE data recovery."""
        try:
            forecasts = await async_fetch_opendpe_forecast(self)
            _LOGGER.debug("Open DPE: %s jours récupérés", len(forecasts))
            return forecasts

        except Exception as exc:
            _LOGGER.error("Open DPE: erreur lors de la mise à jour: %s", exc)
            # raise UpdateFailed(f"Erreur mise à jour des prévisions Open DPE: {exc}")
            async_call_later(self.hass, timedelta(minutes=self.retry_delay), self.async_refresh)
        
    def get_data(self, date: str) -> ForecastSensor | None:
        if date in self.tempo_data:
            return self.tempo_data.get(date)
        return self._cached_data.get(date)


#   Add formated day of week and short date to data
def _format_all_dates(self: ForecastCoordinator, data: list[ForecastDayLight] | list[ForecastDay], lang: str) -> dict[str, ForecastSensor]:
    # Cette fonction s'exécutera dans un thread séparé
    forecasts = {}
    
    # Détermine le format de date court sans l'année selon la locale
    date_fmt = "dd/MM"
    try:
        pattern = get_date_format("short", locale=lang).pattern
        # On enlève l'année (y) et les séparateurs inutiles pour ne garder que jour et mois
        date_fmt = pattern.replace("y", "").replace("Y", "").strip("/.- ")
        # Nettoyage des doubles séparateurs éventuels (ex: // ou ..)
        for sep in ["/", ".", "-", " "]:
            date_fmt = date_fmt.replace(sep + sep, sep)
    except Exception:
        pass

    for f_date in data:
        try:
            # Determine color key based on service type
            color_key = "couleur"
            if self.service_type == OPENDPE_SERVICE_FULL:
                color_key = "tempo_color"

            prob = f_date.get("probability", None)
            color = f_date.get(color_key, "").lower()

            if prob is not None and prob != 1:
                p_blue = f_date.get("probability_bleu") or 0
                p_white = f_date.get("probability_blanc") or 0
                p_red = f_date.get("probability_rouge") or 0

                if p_blue or p_white or p_red:
                    probs = []
                    if p_blue > 0: probs.append((p_blue, COLORS["BLUE"]["emoji"]))
                    if p_white > 0: probs.append((p_white, COLORS["WHITE"]["emoji"]))
                    if p_red > 0: probs.append((p_red, COLORS["RED"]["emoji"]))

                    probs.sort(key=lambda x: x[0])

                    color = "".join(p[1] for p in probs)
                    prob = "-".join(str(p[0]) for p in probs)

            forecast_date = date.fromisoformat(f_date["date"])
            sensor_item = ForecastSensor(
                date        = forecast_date,
                short_date  = format_date(forecast_date, date_fmt, locale=lang),
                day         = format_date(forecast_date, "EEE", locale=lang),
                color       = color,
                probability = prob
                )
            forecasts[f_date["date"]] = sensor_item
            self._cached_data[f_date["date"]] = sensor_item
        except Exception as exc:
            _LOGGER.warning("Open DPE: ligne ignorée (%s) : %s", exc, f_date)
            continue
    return forecasts

#   Main function (Open-DPE)
async def async_fetch_opendpe_forecast(self: ForecastCoordinator) -> dict[str, ForecastSensor]:
    """Fetch Tempo forecasts from the Open DPE JSON."""
    session = self.session
    hass = self.hass
    
    url = OPEN_DPE_LIGHT_URL
    if self.service_type == OPENDPE_SERVICE_FULL:
        url = OPEN_DPE_FULL_URL

    _LOGGER.debug("Open DPE: Service '%s' actif (URL: %s)", self.service_type, url)

    try:
        async with session.get(url, timeout=10) as response:
            if response.status != 200:
                _LOGGER.error("Open-DPE: HTTP %s", response.status)
                async_call_later(self.hass, timedelta(minutes=self.retry_delay), self.async_refresh)
                return self._cached_data

            # Lire le contenu brut pour diagnostic
            response_text = await response.text()
            _LOGGER.debug("[API] Réponse brute (500 premiers chars): %s", response_text[:500])
            data: list[ForecastDayLight] | list[ForecastDay] = json.loads(response_text)

            forecasts = await hass.async_add_executor_job(_format_all_dates, self, data, hass.config.language)
            _LOGGER.debug("Open DPE: forecasts traité brute (500 premiers chars): %s", forecasts)

            return forecasts

    except Exception as exc:
        _LOGGER.error("Open DPE: erreur lors de la récupération JSON : %s", exc)
        async_call_later(self.hass, timedelta(minutes=self.retry_delay), self.async_refresh)
        return self._cached_data