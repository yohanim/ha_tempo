from __future__ import annotations

import logging
from datetime import timedelta
import aiohttp
import asyncio
import async_timeout
import json

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.ssl import get_default_no_verify_context
from homeassistant.helpers.event import async_track_time_change, async_call_later
from homeassistant.util import dt as dt_util

from .const import (
    HP_HOUR,
    RTE_API_URL,
    COLORS,
    RETRY_DELAY_MINUTES,
)
from .utils import get_tempo_date

_LOGGER = logging.getLogger(__name__)

class TempoDataCoordinator(DataUpdateCoordinator):
    """Coordinateur pour récupérer les données RTE Tempo."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialisation du coordinateur."""
        super().__init__(
            hass,
            _LOGGER,
            name="Tempo RTE color",
            update_interval=None,  # Pas de mise à jour automatique, uniquement programmée
        )
        self.tempo_data = {}
        self._cached_data = {}  # Cache pour garder les dernières données valides
        self._last_api_call = None
        self._data_fetched_today = False
        
        # Contexte SSL asynchrone recommandé par Home Assistant
        self._ssl_context = get_default_no_verify_context()

        self._schedule_updates()

    def _schedule_updates(self):
        """Programme les mises à jour aux heures clés."""

        # À {HP_HOUR}h : Changement de jour Tempo
        async_track_time_change(
            self.hass,
            self._trigger_day_change,
            hour=HP_HOUR,
            minute=0,
            second=0
        )

        # À 7h05 : récupération API pour couleur J+1 (décalé de 5min pour éviter la congestion)
        async_track_time_change(
            self.hass,
            self._trigger_api_refresh,
            hour=6,
            minute=35,
            second=0
        )

        _LOGGER.info("Mises à jour programmées: %sh (J HP), 7h05 (API J+1)", HP_HOUR)

    async def _trigger_api_refresh(self, _now=None):
        """Récupération API à 7h pour couleur J+1."""
        now = dt_util.now().astimezone(dt_util.get_time_zone("Europe/Paris"))
        today_date = now.strftime("%Y-%m-%d")
        
        # Évite les appels multiples le même jour
        if self._last_api_call == today_date and self._data_fetched_today:
            _LOGGER.info("Données J+1 déjà récupérées aujourd'hui, skip")
            return
        
        _LOGGER.info("7h05 - Récupération API pour couleur J+1")
        self._last_api_call = today_date
        await self.async_refresh()

    async def _trigger_day_change(self, _now=None):
        """Changement de période HP/HC ou de jour."""
        now = dt_util.now().astimezone(dt_util.get_time_zone("Europe/Paris"))
        
        if now.hour == HP_HOUR:
            _LOGGER.info("%sh - Changement de jour Tempo", HP_HOUR)
            self._data_fetched_today = False  # Reset pour permettre la récupération à 7h
        
        # Force la mise à jour des entités (sans appel API)
        self.async_set_updated_data(self.tempo_data)

    def _validate_and_cache_data(self, new_data: dict) -> bool:
        """Valide les nouvelles données et met à jour le cache si valides."""
        if not new_data:
            _LOGGER.warning("[Validation] Données vides reçues de l'API (dict vide ou None)")
            return False

        today = get_tempo_date(0)
        tomorrow = get_tempo_date(1)

        _LOGGER.debug("[Validation] Date J calculée: %s, Date J+1: %s", today, tomorrow)
        _LOGGER.debug("[Validation] Nombre total d'entrées reçues: %s", len(new_data))

        # Vérifie que les données essentielles sont présentes
        today_color = new_data.get(today)
        tomorrow_color = new_data.get(tomorrow)

        _LOGGER.debug("[Validation] Couleur J (%s): %s", today, today_color)
        _LOGGER.debug("[Validation] Couleur J+1 (%s): %s", tomorrow, tomorrow_color)

        if not today_color:
            _LOGGER.warning("[Validation] Date J (%s) absente des données API", today)
            _LOGGER.debug("[Validation] Dates disponibles (dernières 10): %s", sorted(new_data.keys())[-10:])
            return False

        if today_color not in COLORS:
            _LOGGER.warning("[Validation] Couleur J invalide: '%s' (attendu: %s)", today_color, list(COLORS.keys()))
            return False

        # J+1 peut ne pas encore être disponible (avant 7h)
        if (not tomorrow_color) or (tomorrow_color not in COLORS):
            _LOGGER.warning("[Validation] Couleur J+1 invalide: '%s' (attendu: %s)", tomorrow_color, list(COLORS.keys()))
            return False

        # Mise à jour du cache avec les données valides
        cached_count = 0
        for date, color in new_data.items():
            if color in COLORS:
                self._cached_data[date] = color
                cached_count += 1

        _LOGGER.info("[Validation] Cache mis à jour (%s entrées) - J: %s, J+1: %s", cached_count, today_color, tomorrow_color or 'N/A')
        return True

    async def _async_update_data(self):
        """Récupération des données depuis l'API RTE (tempoLight)."""
        url = RTE_API_URL
        now = dt_util.now().astimezone(dt_util.get_time_zone("Europe/Paris"))

        _LOGGER.debug("[API] Appel API à %s - URL: %s", now.strftime('%H:%M:%S'), url)

        try:
            # Utiliser le contexte SSL pré-créé
            connector = aiohttp.TCPConnector(ssl=self._ssl_context)

            async with async_timeout.timeout(15):
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(url) as response:
                        _LOGGER.debug("[API] Status HTTP: %s", response.status)
                        _LOGGER.debug("[API] Headers: %s", dict(response.headers))

                        if response.status != 200:
                            response_text = await response.text()
                            _LOGGER.error(
                                "[API] Erreur HTTP %s - Réponse: %s",
                                response.status,
                                response_text[:500]
                            )
                            return self._cached_data

                        # Lire le contenu brut pour diagnostic
                        response_text = await response.text()
                        _LOGGER.debug("[API] Réponse brute (500 premiers chars): %s", response_text[:500])

                        try:
                            data = json.loads(response_text)
                        except json.JSONDecodeError as json_err:
                            _LOGGER.error("[API] Erreur parsing JSON: %s", json_err)
                            _LOGGER.error("[API] Contenu reçu: %s", response_text[:1000])
                            return self._cached_data

                        # Log de la structure de la réponse
                        _LOGGER.debug("[API] Clés dans la réponse: %s", list(data.keys()))

                        new_data = data.get("values", {})

                        # Diagnostic détaillé si données vides
                        if not new_data:
                            _LOGGER.warning("[API] Clé 'values' vide ou absente")
                            _LOGGER.warning("[API] Structure complète: %s", data)
                        else:
                            _LOGGER.debug("[API] Nombre d'entrées dans 'values': %s", len(new_data))
                            # Afficher les 5 dernières dates pour vérifier
                            sorted_dates = sorted(new_data.keys())[-5:]
                            _LOGGER.debug("[API] 5 dernières dates: %s", dict((d, new_data[d]) for d in sorted_dates))

                        # Valide et met en cache les données
                        if self._validate_and_cache_data(new_data):
                            self.tempo_data = new_data
                            self._data_fetched_today = True

                            today = get_tempo_date(0)
                            tomorrow = get_tempo_date(1)

                            _LOGGER.info(
                                "✓ Données Tempo récupérées: J=%s (%s), J+1=%s (%s)", 
                                today, self.tempo_data[today], 
                                tomorrow, self.tempo_data[tomorrow]
                            )
                        else:
                            _LOGGER.warning("[API] Données invalides, conservation du cache")
                            return self._cached_data

                        return self.tempo_data

        except asyncio.TimeoutError:
            _LOGGER.error("[API] Timeout (15s) lors de la récupération des données")
            async_call_later(self.hass, timedelta(minutes=RETRY_DELAY_MINUTES), self.async_refresh)
            return self._cached_data
        except aiohttp.ClientError as err:
            _LOGGER.error("[API] Erreur de connexion: %s", err)
            async_call_later(self.hass, timedelta(minutes=RETRY_DELAY_MINUTES), self.async_refresh)
            return self._cached_data
        except Exception as err:
            _LOGGER.error("[API] Erreur inattendue: %s", err, exc_info=True)
            async_call_later(self.hass, timedelta(minutes=RETRY_DELAY_MINUTES), self.async_refresh)
            return self._cached_data
        
    def get_data(self, date) -> str|None:
        if date in self.tempo_data:
            return self.tempo_data.get(date)
        return self._cached_data.get(date, "inconnu")