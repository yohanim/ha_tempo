from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, time
from typing import Any
import aiohttp
import asyncio
import async_timeout
import json

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change, async_call_later
from homeassistant.util import dt as dt_util

from .const import (
    TEMPO_DAY_CHANGE_TIME,
    RTE_API_URL,
    RTE_API_FULL_URL,
    COLORS,
    TEMPO_RETRY_DELAY_MINUTES,
    CONF_TEMPO_DAY_CHANGE_TIME,
    CONF_TEMPO_RETRY_DELAY,
    CONF_RTE_TEMPO_COLOR_REFRESH_TIME,
    DEFAULT_RTE_TEMPO_COLOR_REFRESH_TIME,
    CONF_EDF_TEMPO_COLOR_REFRESH_TIME,
    DEFAULT_EDF_TEMPO_COLOR_REFRESH_TIME,
)
from .utils import get_tempo_date, get_tempo_season

_LOGGER = logging.getLogger(__name__)

class TempoDataCoordinator(DataUpdateCoordinator):
    """Coordinateur pour récupérer les données RTE Tempo."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialisation du coordinateur."""
        super().__init__(
            hass,
            _LOGGER,
            name="Tempo RTE color",
            update_interval=None,  # Pas de mise à jour automatique, uniquement programmée
        )
        self.entry = entry
        self.tempo_day_change_time_str = entry.options.get(CONF_TEMPO_DAY_CHANGE_TIME, TEMPO_DAY_CHANGE_TIME)
        self.tempo_day_change_time = time.fromisoformat(self.tempo_day_change_time_str)
        self.rte_tempo_refresh_time_str = entry.options.get(CONF_RTE_TEMPO_COLOR_REFRESH_TIME, DEFAULT_RTE_TEMPO_COLOR_REFRESH_TIME)
        self.rte_tempo_refresh_time = time.fromisoformat(self.rte_tempo_refresh_time_str)
        self.edf_tempo_refresh_time_str = entry.options.get(CONF_EDF_TEMPO_COLOR_REFRESH_TIME, DEFAULT_EDF_TEMPO_COLOR_REFRESH_TIME)
        self.edf_tempo_refresh_time = time.fromisoformat(self.edf_tempo_refresh_time_str)
        self.retry_delay = entry.options.get(CONF_TEMPO_RETRY_DELAY, TEMPO_RETRY_DELAY_MINUTES)

        self.tempo_data = {}
        self._cached_data = {}  # Cache pour garder les dernières données valides
        self._last_api_call = None
        self._data_fetched_today = False
        self._scheduled_listeners: list = []
        self._retry_unsub = None
        
        # Utilisation d'une session partagée. La vérification SSL est activée par défaut.
        self.session = async_get_clientsession(hass)

        self._schedule_updates()

    def _schedule_updates(self) -> None:
        """Programme les mises à jour aux heures clés."""

        # Au moment du changement de jour Tempo
        self._scheduled_listeners.append(
            async_track_time_change(
                self.hass,
                self._trigger_day_change,
                hour=self.tempo_day_change_time.hour,
                minute=self.tempo_day_change_time.minute,
                second=self.tempo_day_change_time.second,
            )
        )

        # À {self.rte_tempo_refresh_time_str} : récupération API pour couleur J+1
        self._scheduled_listeners.append(
            async_track_time_change(
                self.hass,
                self._trigger_api_refresh,
                hour=self.rte_tempo_refresh_time.hour,
                minute=self.rte_tempo_refresh_time.minute,
                second=self.rte_tempo_refresh_time.second,
            )
        )

        # À {self.edf_tempo_refresh_time_str} : récupération API pour couleur J+1 (EDF)
        self._scheduled_listeners.append(
            async_track_time_change(
                self.hass,
                self._trigger_api_refresh,
                hour=self.edf_tempo_refresh_time.hour,
                minute=self.edf_tempo_refresh_time.minute,
                second=self.edf_tempo_refresh_time.second,
            )
        )

        _LOGGER.info("Mises à jour programmées: %s (Changement jour Tempo), %s (API RTE), %s (API EDF)", self.tempo_day_change_time_str, self.rte_tempo_refresh_time_str, self.edf_tempo_refresh_time_str)

    async def _trigger_api_refresh(self, _now: datetime | None = None) -> None:
        """Récupération API à 7h pour couleur J+1."""
        now = dt_util.now().astimezone(dt_util.get_time_zone("Europe/Paris"))
        today_date = now.strftime("%Y-%m-%d")
        
        # Évite les appels multiples le même jour
        if self._last_api_call == today_date and self._data_fetched_today:
            _LOGGER.info("Données J+1 déjà récupérées aujourd'hui, skip")
            return
        
        _LOGGER.info("%s - Récupération API pour couleur J+1", now.strftime("%H:%M:%S"))
        self._last_api_call = today_date
        await self.async_refresh()

    async def _trigger_day_change(self, _now: datetime | None = None) -> None:
        """Changement de période HP/HC ou de jour."""
        now = dt_util.now().astimezone(dt_util.get_time_zone("Europe/Paris"))
        
        if now.hour == self.tempo_day_change_time.hour and now.minute == self.tempo_day_change_time.minute:
            _LOGGER.info("%s - Changement de jour Tempo", self.tempo_day_change_time_str)
            self._data_fetched_today = False  # Reset pour permettre la récupération à 7h
        
        # Force la mise à jour des entités (sans appel API)
        self.async_set_updated_data(self.tempo_data)

    async def _async_retry_refresh(self, _now: datetime) -> None:
        """Retry callback compatible with async_call_later."""
        self._retry_unsub = None
        await self.async_refresh()

    def _schedule_retry(self) -> None:
        """Schedule one retry refresh if not already planned."""
        if self._retry_unsub is not None:
            return
        self._retry_unsub = async_call_later(
            self.hass,
            timedelta(minutes=self.retry_delay),
            self._async_retry_refresh,
        )

    def _validate_and_cache_data(self, new_data: dict[str, Any]) -> bool:
        """Valide les nouvelles données et met à jour le cache si valides."""
        if not new_data:
            _LOGGER.warning("[Validation] Données vides reçues de l'API (dict vide ou None)")
            return False

        # Normalise les données en minuscules
        normalized_data = {d: c.lower() if c else None for d, c in new_data.items()}

        today = get_tempo_date(0, self.tempo_day_change_time_str)
        tomorrow = get_tempo_date(1, self.tempo_day_change_time_str)

        _LOGGER.debug("[Validation] Date J calculée: %s, Date J+1: %s", today, tomorrow)
        _LOGGER.debug("[Validation] Nombre total d'entrées reçues: %s", len(normalized_data))

        # Vérifie que les données essentielles sont présentes
        today_color = normalized_data.get(today)
        tomorrow_color = normalized_data.get(tomorrow)

        # Mise à jour du cache avec les données valides
        valid_entries = {d: c for d, c in normalized_data.items() if c in COLORS}
        self._cached_data.update(valid_entries)
        cached_count = len(valid_entries)
        _LOGGER.info("[Validation] Cache mis à jour (%s entrées) - J: %s, J+1: %s", cached_count, today_color, tomorrow_color or 'N/A')

        _LOGGER.debug("[Validation] Couleur J (%s): %s", today, today_color)
        _LOGGER.debug("[Validation] Couleur J+1 (%s): %s", tomorrow, tomorrow_color)

        if not today_color:
            _LOGGER.warning("[Validation] Date J (%s) absente des données API", today)
            _LOGGER.debug("[Validation] Dates disponibles (dernières 10): %s", sorted(normalized_data.keys())[-10:])
            return False

        if today_color not in COLORS:
            _LOGGER.warning("[Validation] Couleur J invalide: '%s' (attendu: %s)", today_color, list(COLORS.keys()))
            return False

        # J+1 peut ne pas encore être disponible (avant 7h)
        if (not tomorrow_color) or (tomorrow_color not in COLORS):
            _LOGGER.warning("[Validation] Couleur J+1 invalide: '%s' (attendu: %s)", tomorrow_color, list(COLORS.keys()))
            return False

        self.tempo_data = normalized_data
        return True

    async def _fetch_rte_data(self, url: str) -> dict[str, Any] | None:
        """Récupère les données JSON depuis une URL RTE donnée."""
        now = dt_util.now().astimezone(dt_util.get_time_zone("Europe/Paris"))
        _LOGGER.debug("[API] Appel API à %s - URL: %s", now.strftime('%H:%M:%S'), url)

        try:
            async with async_timeout.timeout(15):
                async with self.session.get(url) as response:
                    _LOGGER.debug("[API] Status HTTP: %s", response.status)
                    _LOGGER.debug("[API] Headers: %s", dict(response.headers))

                    if response.status != 200:
                        response_text = await response.text()
                        _LOGGER.error(
                            "[API] Erreur HTTP %s - Réponse: %s",
                            response.status,
                            response_text[:500]
                        )
                        return None

                    # Lire le contenu brut pour diagnostic
                    response_text = await response.text()
                    _LOGGER.debug("[API] Réponse brute (500 premiers chars): %s", response_text[:500])

                    try:
                        data = json.loads(response_text)
                        return data
                    except json.JSONDecodeError as json_err:
                        _LOGGER.error("[API] Erreur parsing JSON: %s", json_err)
                        _LOGGER.error("[API] Contenu reçu: %s", response_text[:1000])
                        return None

        except asyncio.TimeoutError:
            _LOGGER.error("[API] Timeout (15s) lors de la récupération des données")
            return None
        except aiohttp.ClientError as err:
            _LOGGER.error("[API] Erreur de connexion: %s", err)
            return None
        except Exception as err:
            _LOGGER.error("[API] Erreur inattendue: %s", err, exc_info=True)
            return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Récupération des données depuis l'API RTE (tempoLight) avec fallback."""
        today = get_tempo_date(0, self.tempo_day_change_time_str)
        
        # 1. Tentative avec l'API Light (standard)
        data = await self._fetch_rte_data(RTE_API_URL)
        values = data.get("values", {}) if data else {}
        if not isinstance(values, dict):
            values = {}

        # 2. Si pas de valeur pour aujourd'hui, tentative avec l'API Full
        # (On n'appelle pas l'API Full si c'est juste demain qui manque)
        if today not in values:
            _LOGGER.info("Données incomplètes (J manquante) sur l'API Light, tentative sur l'API Full")
            today_dt = date.fromisoformat(today)
            season = get_tempo_season(today_dt)
            data_full = await self._fetch_rte_data(RTE_API_FULL_URL.format(season=season))
            if data_full:
                values_full = data_full.get("values", {})
                # On prend les données Full si elles existent
                if isinstance(values_full, dict) and values_full:
                    values = values_full

        # 3. Traitement des données récupérées (Light ou Full)
        if values:
            # Log de diagnostic
            _LOGGER.debug("[API] Nombre d'entrées dans 'values': %s", len(values))
            if _LOGGER.isEnabledFor(logging.DEBUG):
                sorted_dates = sorted(values.keys())[-5:]
                _LOGGER.debug("[API] 5 dernières dates: %s", dict((d, values[d]) for d in sorted_dates))

            # Valide et met en cache les données
            if self._validate_and_cache_data(values):
                self._data_fetched_today = True

                tomorrow = get_tempo_date(1, self.tempo_day_change_time_str)
                _LOGGER.info(
                    "✓ Données Tempo récupérées: J=%s (%s), J+1=%s (%s)", 
                    today, self.tempo_data[today], 
                    tomorrow, self.tempo_data.get(tomorrow, 'N/A')
                )
                return self.tempo_data
            else:
                _LOGGER.warning("[API] Données invalides après validation, conservation du cache")
        else:
            _LOGGER.warning("[API] Aucune donnée valide récupérée (ni Light, ni Full)")

        # Si on arrive ici, c'est un échec : on planifie un retry
        self._schedule_retry()
        return self._cached_data

    async def async_shutdown(self) -> None:
        """Release listeners and pending retry callbacks."""
        for remove_listener in self._scheduled_listeners:
            remove_listener()
        self._scheduled_listeners.clear()
        if self._retry_unsub is not None:
            self._retry_unsub()
            self._retry_unsub = None

    def get_data(self, date: str) -> str | None:
        if date in self.tempo_data:
            return self.tempo_data.get(date)
        return self._cached_data.get(date, None)