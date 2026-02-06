import logging
from homeassistant.util import dt as dt_util
from datetime import timedelta
from .const import (
    HP_HOUR,
    COLORS,
)

def get_tempo_date(offset_days: int = 0) -> str:
    """
    Retourne la date Tempo (en tenant compte du décalage {HP_HOUR}h).
    offset_days: 0 pour J, 1 pour J+1
    """
    # now = dt_util.now().astimezone(dt_util.get_time_zone("Europe/Paris"))
    
    # Si avant 6h du matin, on considère que c'est encore la veille
    # if now.hour < 6:
    #     now = now - timedelta(days=1)
    
    target_date = dt_util.now().astimezone(dt_util.get_time_zone("Europe/Paris")) - timedelta(hours=HP_HOUR) + timedelta(days=offset_days)
    return target_date.strftime("%Y-%m-%d")

def get_color_code(data: str) -> int:
    """Retourne le code couleur pour une date donnée (avec cache)."""
    # Essaie d'abord les données actuelles
    if data and data in COLORS:
        return COLORS[data]["code"]
    
    return COLORS["inconnu"]["code"]

def get_color_name(data: str) -> str:
    """Retourne le nom de la couleur pour une date donnée (avec cache)."""
    if data and data in COLORS:
        return COLORS[data]["name"]
    
    return COLORS["inconnu"]["name"]

def get_color_name_en(data: str) -> str:
    """Retourne le nom anglais de la couleur pour une date donnée (avec cache)."""
    if data and data in COLORS:
        return COLORS[data]["name_en"]
    
    return COLORS["inconnu"]["name_en"]

def get_color_emoji(data: str) -> str:
    """Retourne l'emoji de la couleur pour une date donnée (avec cache)."""
    if data and data in COLORS:
        return COLORS[data]["emoji"]
    
    return COLORS["inconnu"]["emoji"]