from __future__ import annotations

from dataclasses import dataclass
import datetime
from typing import Optional

from .const import (
    COLORS,
    )

#   Forecast model
@dataclass
class ForecastDayLight:
    """Tempo forecast for a given day."""

    date: datetime.date
    couleur: str                                        # "bleu", "blanc", "rouge" (normalized to lowercase)
    probability: Optional[float]                        # 0.67 for example (for 67%)
    source: str = "open_dpe"

@dataclass
class ForecastDay:
    """Tempo forecast for a given day."""

    date: datetime.date
    forecast: int
    consumption_net: int
    stock_blanc: int
    stock_rouge: int
    tempo_color: str                                    # "bleu", "blanc", "rouge" (normalized to lowercase)
    probability: Optional[float]                        # 0.67 for example (for 67%)
    probability_bleu: Optional[float]
    probability_blanc: Optional[float]
    probability_rouge: Optional[float]
    source: str = "open_dpe"

@dataclass
class ForecastSensor:
    """Tempo forecast for a given day."""

    date: datetime.date
    short_date: str                                     # minimized localized date
    day: str                                            # minimized localized day of week
    color: str                                          # "bleu", "blanc", "rouge" (normalized to lowercase)
    probability: Optional[float]                        # 0.67 for example (for 67%)
    source: str = "open_dpe"


#   Tempo color model
@dataclass
class RTEDay:
    """RTE tempo color for a given day."""

    date: datetime.date
    color_emoji: str                                    # color emoji
    color_code: int = 0                                 # color code
    color_name: str = COLORS["inconnu"]["name"]         # color name in French
    color_name_en: str = COLORS["inconnu"]["name_en"]   # color name in English
    source: str = "RTE"