"""Constants for the EDF Tempo integration."""
DOMAIN = "tempo_rte_forecast"
DEVICE_NAME = "Tempo RTE & Open DPE Forecast"
RTE_API_URL = "https://www.services-rte.com/cms/open_data/v1/tempoLight"
RTE_API_FULL_URL = "https://www.services-rte.com/cms/open_data/v1/tempo?season=2025-2026"
OPEN_DPE_URL = "https://open-dpe.fr/assets/tempo_days_lite.json"
COLORS = {
    "BLUE": {"code": 1, "name": "Bleu", "name_en": "blue", "emoji":"🔵"},
    "WHITE": {"code": 2, "name": "Blanc", "name_en": "white","emoji":"⚪"},
    "RED": {"code": 3, "name": "Rouge", "name_en": "red","emoji":"🔴"},
    "inconnu": {"code": 0, "name": "Inconnu", "name_en": "unknown", "emoji":"❓"},
}
COLORS["bleu"] = COLORS["BLUE"]
COLORS["blanc"] = COLORS["WHITE"]
COLORS["rouge"] = COLORS["RED"]
# SENSOR_COLOR_BLUE_EMOJI = COLORS["BLUE"]["emoji"]
# SENSOR_COLOR_WHITE_EMOJI = COLORS["WHITE"]["emoji"]
# SENSOR_COLOR_RED_EMOJI = COLORS["RED"]["emoji"]
# SENSOR_COLOR_UNKNOWN_EMOJI = COLORS["inconnu"]["emoji"]
# SENSOR_COLOR_BLUE_NAME = COLORS["BLUE"]["name"]
# SENSOR_COLOR_WHITE_NAME = COLORS["WHITE"]["name"]
# SENSOR_COLOR_RED_NAME = COLORS["RED"]["name"]
# SENSOR_COLOR_UNKNOWN_NAME = COLORS["inconnu"]["name"]

TEMPO_DAY_CHANGE_HOUR = 6
HC_HOUR = 22

TEMPO_RETRY_DELAY_MINUTES = 30
FORECAST_RETRY_DELAY_MINUTES = 5

# For forecast
DEVICE_MANUFACTURER = "RTE"
DEVICE_MODEL = "Calendrier Tempo"

# DAYS_FR = ['Lun.', 'Mar.', 'Mer.', 'Jeu.', 'Ven.', 'Sam.', 'Dim.']

CONF_TEMPO_DAY_CHANGE_HOUR = "tempo_day_change_hour"
CONF_TEMPO_RETRY_DELAY = "tempo_retry_delay_minutes"
CONF_FORECAST_RETRY_DELAY = "forecast_retry_delay_minutes"