from __future__ import annotations
from datetime import date, datetime, timedelta, time
import logging
from homeassistant.util import dt as dt_util
from .const import (
    TEMPO_DAY_CHANGE_TIME,
    COLORS,
)

def get_tempo_date(offset_days: int = 0, tempo_day_change_time_str: str = TEMPO_DAY_CHANGE_TIME) -> str:
    _LOGGER = logging.getLogger(__name__)

    """
    Retourne la date Tempo (en tenant compte de l'heure de changement).
    offset_days: 0 pour J, 1 pour J+1
    """
    now = dt_util.now(dt_util.get_time_zone("Europe/Paris"))
    change_time = time.fromisoformat(tempo_day_change_time_str)
    change_time_delta = timedelta(hours=change_time.hour, minutes=change_time.minute, seconds=change_time.second)

    target_date = now - change_time_delta + timedelta(days=offset_days)
    return target_date.strftime("%Y-%m-%d")

def parse_offpeak_ranges(ranges_str: str) -> list[tuple[time, time]]:
    """Parse a string of time ranges into a list of time tuples."""
    _LOGGER = logging.getLogger(__name__)
    ranges = []
    if not ranges_str:
        return ranges
    for part in ranges_str.split(','):
        part = part.strip()
        if not part:
            continue
        try:
            start_str, end_str = part.split('-')
            start_time = time.fromisoformat(start_str.strip())
            end_time = time.fromisoformat(end_str.strip())
            ranges.append((start_time, end_time))
        except ValueError as e:
            _LOGGER.error("Plage horaire invalide '%s': %s", part, e)
    return ranges

def is_offpeak(now: datetime, offpeak_ranges: list[tuple[time, time]]) -> bool:
    """Check if the current time is within any of the off-peak ranges."""
    current_time = now.time()
    for start_time, end_time in offpeak_ranges:
        # Case 1: Range does not cross midnight (e.g., 01:00-05:00)
        if start_time < end_time:
            if start_time <= current_time < end_time:
                return True
        # Case 2: Range crosses midnight (e.g., 22:00-06:00)
        else:
            if current_time >= start_time or current_time < end_time:
                return True
    return False

def get_tempo_season(date_ref: date | datetime | None = None) -> str:
    """Retourne la saison Tempo actuelle (ex: '2024-2025'). Changement au 1er août."""
    if date_ref is None:
        date_ref = dt_util.now()
        
    # La saison commence le 1er août. Si mois < 8, on est dans la saison commencée l'année précédente.
    start_year = date_ref.year - (1 if date_ref.month < 8 else 0)
    
    return f"{start_year}-{start_year + 1}"

def get_color_code(data: str | None) -> int:
    """Retourne le code couleur pour une date donnée (avec cache)."""
    # Essaie d'abord les données actuelles
    if data and data in COLORS:
        return COLORS[data]["code"]
    
    return COLORS["inconnu"]["code"]

def get_color_name(data: str | None) -> str:
    """Retourne le nom de la couleur pour une date donnée (avec cache)."""
    if data and data in COLORS:
        return COLORS[data]["name"]
    
    return COLORS["inconnu"]["name"]

def get_color_name_en(data: str | None) -> str:
    """Retourne le nom anglais de la couleur pour une date donnée (avec cache)."""
    if data and data in COLORS:
        return COLORS[data]["name_en"]
    
    return COLORS["inconnu"]["name_en"]

def get_color_emoji(data: str | None) -> str:
    """Retourne l'emoji de la couleur pour une date donnée (avec cache)."""
    if data and data in COLORS:
        return COLORS[data]["emoji"]
    
    return COLORS["inconnu"]["emoji"]