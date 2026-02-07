from __future__ import annotations
from datetime import date, datetime, timedelta
from homeassistant.util import dt as dt_util
from .const import (
    TEMPO_DAY_CHANGE_HOUR,
    COLORS,
)

def get_tempo_date(offset_days: int = 0, tempo_day_change_hour: int = TEMPO_DAY_CHANGE_HOUR) -> str:
    """
    Retourne la date Tempo (en tenant compte du décalage {TEMPO_DAY_CHANGE_HOUR}h).
    offset_days: 0 pour J, 1 pour J+1
    """
    # Optimisation : récupération directe du fuseau Paris et combinaison des deltas
    target_date = dt_util.now(dt_util.get_time_zone("Europe/Paris")) + timedelta(days=offset_days, hours=-tempo_day_change_hour)
    return target_date.strftime("%Y-%m-%d")

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