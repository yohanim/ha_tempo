from __future__ import annotations

import logging
from datetime import date, datetime, time
from collections.abc import Sequence
from typing import Any
import aiohttp
import async_timeout
import json

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .coordinator_retry import RetryWhenNoUpdateIntervalMixin
from .const import (
    TEMPO_DAY_CHANGE_TIME,
    RTE_API_URL,
    RTE_API_FULL_URL,
    COULEUR_TEMPO_API_BASE,
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

class TempoDataCoordinator(RetryWhenNoUpdateIntervalMixin, DataUpdateCoordinator):
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

    async def _fetch_json_url(
        self,
        url: str,
        log_prefix: str,
        *,
        params: Sequence[tuple[str, str]] | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        """GET JSON générique (RTE ou api-couleur-tempo.fr)."""
        now = dt_util.now().astimezone(dt_util.get_time_zone("Europe/Paris"))
        _LOGGER.debug(
            "%s Appel à %s — URL: %s params=%s",
            log_prefix,
            now.strftime("%H:%M:%S"),
            url,
            params,
        )

        try:
            async with async_timeout.timeout(15):
                async with self.session.get(url, params=params) as response:
                    _LOGGER.debug("%s Status HTTP: %s", log_prefix, response.status)

                    if response.status != 200:
                        response_text = await response.text()
                        snippet = response_text[:500]
                        if response.status >= 500:
                            _LOGGER.warning(
                                "%s HTTP %s (service may be in maintenance) — %s",
                                log_prefix,
                                response.status,
                                snippet,
                            )
                        else:
                            _LOGGER.error(
                                "%s Erreur HTTP %s — %s",
                                log_prefix,
                                response.status,
                                snippet,
                            )
                        return None

                    response_text = await response.text()
                    _LOGGER.debug("%s Réponse (500 premiers chars): %s", log_prefix, response_text[:500])

                    try:
                        data = json.loads(response_text)
                        return data
                    except json.JSONDecodeError as json_err:
                        _LOGGER.error("%s Erreur parsing JSON: %s", log_prefix, json_err)
                        _LOGGER.error("%s Contenu: %s", log_prefix, response_text[:1000])
                        return None

        except TimeoutError:
            _LOGGER.error("%s Timeout (15s)", log_prefix)
            return None
        except aiohttp.ClientError as err:
            _LOGGER.error("%s Erreur de connexion: %s", log_prefix, err)
            return None
        except Exception as err:
            _LOGGER.error("%s Erreur inattendue: %s", log_prefix, err, exc_info=True)
            return None

    async def _fetch_rte_data(self, url: str) -> dict[str, Any] | None:
        """Récupère les données JSON depuis une URL RTE donnée."""
        raw = await self._fetch_json_url(url, "[RTE]")
        if raw is None or isinstance(raw, list):
            return None
        return raw

    @staticmethod
    def _day_needs_couleur_tempo_fill(values: dict[str, Any], day: str) -> bool:
        """True si la date n'a pas encore une couleur bleu/blanc/rouge exploitable."""
        raw = values.get(day)
        if raw is None:
            return True
        if not isinstance(raw, str):
            return True
        k = raw.strip().lower()
        return k not in ("blue", "white", "red")

    @staticmethod
    def _couleur_tempo_payload_to_color_key(payload: dict[str, Any] | None) -> str | None:
        """Mappe la réponse JourTempo (api-couleur-tempo.fr) vers blue/white/red."""
        if not payload:
            return None
        code = payload.get("codeJour")
        if code in (1, 2, 3):
            return {1: "blue", 2: "white", 3: "red"}[code]
        if code == 0:
            return None
        lib = (payload.get("libCouleur") or "").strip().lower()
        mapping = {"bleu": "blue", "blanc": "white", "rouge": "red"}
        return mapping.get(lib)

    async def _apply_couleur_tempo_buffer(
        self, values: dict[str, Any], today: str, tomorrow: str
    ) -> None:
        """Complète J / J+1 via GET /api/joursTempo?dateJour[]=… (une requête pour toutes les dates manquantes)."""
        missing = [
            d
            for d in (today, tomorrow)
            if self._day_needs_couleur_tempo_fill(values, d)
        ]
        if not missing:
            return

        batch_url = f"{COULEUR_TEMPO_API_BASE}/api/joursTempo"
        query_params: list[tuple[str, str]] = [("dateJour[]", d) for d in missing]
        raw = await self._fetch_json_url(
            batch_url, "[CouleurTempo]", params=query_params
        )
        if raw is None:
            return
        if not isinstance(raw, list):
            _LOGGER.warning(
                "[CouleurTempo] Réponse /api/joursTempo inattendue (type %s)",
                type(raw).__name__,
            )
            return

        missing_set = set(missing)
        for payload in raw:
            if not isinstance(payload, dict):
                continue
            day = payload.get("dateJour")
            if not isinstance(day, str) or day not in missing_set:
                continue
            color = self._couleur_tempo_payload_to_color_key(payload)
            if not color:
                _LOGGER.debug(
                    "[CouleurTempo] Pas de couleur exploitable pour %s (code 0 / indispo)",
                    day,
                )
                continue
            values[day] = color
            _LOGGER.info("[CouleurTempo] Complément pour %s: %s", day, color)

    async def _async_update_data(self) -> dict[str, Any]:
        """Récupération des données depuis l'API RTE (tempoLight) avec fallback."""
        today = get_tempo_date(0, self.tempo_day_change_time_str)
        tomorrow = get_tempo_date(1, self.tempo_day_change_time_str)

        # 1. API RTE tempoLight
        data = await self._fetch_rte_data(RTE_API_URL)
        values: dict[str, Any] = {}
        if data:
            v = data.get("values", {})
            if isinstance(v, dict):
                values = dict(v)

        # 2. Tampon api-couleur-tempo.fr (données RTE agrégées) pour J / J+1 manquants
        await self._apply_couleur_tempo_buffer(values, today, tomorrow)

        # 3. Dernier recours : calendrier saison API Full RTE
        if self._day_needs_couleur_tempo_fill(values, today) or self._day_needs_couleur_tempo_fill(
            values, tomorrow
        ):
            _LOGGER.info(
                "Données encore incomplètes après api-couleur-tempo, tentative API Full RTE"
            )
            today_dt = date.fromisoformat(today)
            season = get_tempo_season(today_dt)
            data_full = await self._fetch_rte_data(RTE_API_FULL_URL.format(season=season))
            if data_full:
                values_full = data_full.get("values", {})
                if isinstance(values_full, dict) and values_full:
                    values = values_full

        # 4. Traitement des données récupérées (Light, tampon, ou Full)
        if values:
            # Log de diagnostic
            _LOGGER.debug("[API] Nombre d'entrées dans 'values': %s", len(values))
            if _LOGGER.isEnabledFor(logging.DEBUG):
                sorted_dates = sorted(values.keys())[-5:]
                _LOGGER.debug("[API] 5 dernières dates: %s", dict((d, values[d]) for d in sorted_dates))

            # Valide et met en cache les données
            if self._validate_and_cache_data(values):
                self._data_fetched_today = True

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

        # Échec sans cache
        if not self._cached_data:
            raise UpdateFailed(
                "RTE Tempo API unavailable and no cached data available",
                retry_after=float(self.retry_delay * 60),
            )
        # Cache encore exploitable : échec de mise à jour (last_update_success=False) + retry_after
        raise UpdateFailed(
            "RTE Tempo API failed; serving cached data",
            retry_after=float(self.retry_delay * 60),
        )

    async def async_shutdown(self) -> None:
        """Release scheduled listeners and coordinator timers."""
        for remove_listener in self._scheduled_listeners:
            remove_listener()
        self._scheduled_listeners.clear()
        await super().async_shutdown()

    def get_data(self, date: str) -> str | None:
        if date in self.tempo_data:
            return self.tempo_data.get(date)
        return self._cached_data.get(date, None)