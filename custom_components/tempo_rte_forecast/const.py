"""Constants for the EDF Tempo integration."""
DOMAIN = "tempo_rte_forecast"
DEVICE_NAME = "Tempo RTE & Open DPE Forecast"
RTE_API_URL = "https://www.services-rte.com/cms/open_data/v1/tempoLight"
RTE_API_FULL_URL = "https://www.services-rte.com/cms/open_data/v1/tempo?season={season}"
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

TEMPO_DAY_CHANGE_TIME = "06:00:00"
HC_HOUR = 22

TEMPO_RETRY_DELAY_MINUTES = 30
FORECAST_RETRY_DELAY_MINUTES = 5

# For forecast
DEVICE_MANUFACTURER = "RTE"
DEVICE_MODEL = "Calendrier Tempo"

# DAYS_FR = ['Lun.', 'Mar.', 'Mer.', 'Jeu.', 'Ven.', 'Sam.', 'Dim.']

CONF_TEMPO_DAY_CHANGE_TIME = "tempo_day_change_time"
CONF_TEMPO_RETRY_DELAY = "tempo_retry_delay_minutes"
CONF_FORECAST_RETRY_DELAY = "forecast_retry_delay_minutes"
CONF_RTE_TEMPO_COLOR_REFRESH_TIME = "rte_tempo_color_refresh_time"
DEFAULT_RTE_TEMPO_COLOR_REFRESH_TIME = "07:05:00"
CONF_EDF_TEMPO_COLOR_REFRESH_TIME = "edf_tempo_color_refresh_time"
DEFAULT_EDF_TEMPO_COLOR_REFRESH_TIME = "11:05:00"

# For tariffs
# For prices
CONF_CONTRACT = "contract"
CONF_OFFPEAK_RANGES = "offpeak_ranges"
DEFAULT_OFFPEAK_RANGES = "22:00-06:00"
CONF_SUBSCRIBED_POWER = "subscribed_power"
DEFAULT_SUBSCRIBED_POWER = "9"
CONF_PRICE_UPDATE_INTERVAL = "price_update_interval"
DEFAULT_PRICE_UPDATE_INTERVAL = 1
PRICE_BASE_URL="https://www.data.gouv.fr/fr/datasets/r/c13d05e5-9e55-4d03-bf7e-042a2ade7e49"
PRICE_HPHC_URL="https://www.data.gouv.fr/fr/datasets/r/f7303b3a-93c7-4242-813d-84919034c416"
PRICE_TEMPO_URL="https://www.data.gouv.fr/fr/datasets/r/0c3d1d36-c412-4620-8566-e5cbb4fa2b5a"