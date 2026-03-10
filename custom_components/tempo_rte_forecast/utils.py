from __future__ import annotations
from datetime import date, datetime, timedelta, time
import logging
from homeassistant.util import dt as dt_util
from .const import (
    TEMPO_DAY_CHANGE_TIME,
    COLORS,
    CONF_ICON_COLOR_BLUE,
    CONF_ICON_COLOR_WHITE,
    CONF_ICON_COLOR_RED,
    CONF_ICON_COLOR_UNKNOWN,
    DEFAULT_ICON_COLOR_BLUE,
    DEFAULT_ICON_COLOR_WHITE,
    DEFAULT_ICON_COLOR_RED,
    DEFAULT_ICON_COLOR_UNKNOWN,
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

def normalize_color(color: str | None) -> str:
    """Normalize color name to English key."""
    if not color:
        return "unknown"
    color = color.lower()
    mapping = {
        "bleu": "blue",
        "blue": "blue",
        "blanc": "white",
        "white": "white",
        "rouge": "red",
        "red": "red",
    }
    return mapping.get(color, color)

def get_icon_color(options: dict, color_key: str) -> str:
    """Get icon color from options."""
    if color_key == "blue":
        return options.get(CONF_ICON_COLOR_BLUE, DEFAULT_ICON_COLOR_BLUE)
    if color_key == "white":
        return options.get(CONF_ICON_COLOR_WHITE, DEFAULT_ICON_COLOR_WHITE)
    if color_key == "red":
        return options.get(CONF_ICON_COLOR_RED, DEFAULT_ICON_COLOR_RED)
    return options.get(CONF_ICON_COLOR_UNKNOWN, DEFAULT_ICON_COLOR_UNKNOWN)

def get_color_code(data: str | None) -> int:
    """Retourne le code couleur pour une date donnée (avec cache)."""
    color_key = normalize_color(data)
    if color_key in COLORS:
        return COLORS[color_key]["code"]
    
    return COLORS["unknown"]["code"]

def get_color_name(data: str | None) -> str:
    """Retourne le nom de la couleur pour une date donnée (avec cache)."""
    color_key = normalize_color(data)
    if color_key in COLORS:
        return COLORS[color_key]["name"]
    
    return COLORS["unknown"]["name"]

def get_color_name_en(data: str | None) -> str:
    """Retourne le nom anglais de la couleur pour une date donnée (avec cache)."""
    color_key = normalize_color(data)
    if color_key in COLORS:
        return COLORS[color_key]["name_en"]
    
    return COLORS["unknown"]["name_en"]

def get_color_emoji(data: str | None) -> str:
    """Retourne l'emoji de la couleur pour une date donnée (avec cache)."""
    color_key = normalize_color(data)
    if color_key in COLORS:
        return COLORS[color_key]["emoji"]
    
    return COLORS["unknown"]["emoji"]
