"""Constants for the EDF Tempo integration."""
DOMAIN = "tempo"
API_URL = "https://www.services-rte.com/cms/open_data/v1/tempoLight"
COLORS = {
    "BLUE": {"code": 1, "name": "Bleu", "name_en": "blue", "emoji":"🔵"},
    "WHITE": {"code": 2, "name": "Blanc", "name_en": "white","emoji":"⚪"},
    "RED": {"code": 3, "name": "Rouge", "name_en": "red","emoji":"🔴"},
}
SENSOR_COLOR_BLUE_EMOJI = COLORS["BLUE"]["emoji"]
SENSOR_COLOR_WHITE_EMOJI = COLORS["WHITE"]["emoji"]
SENSOR_COLOR_RED_EMOJI = COLORS["RED"]["emoji"]
SENSOR_COLOR_UNKNOWN_EMOJI = "❓"
SENSOR_COLOR_BLUE_NAME = COLORS["BLUE"]["name"]
SENSOR_COLOR_WHITE_NAME = COLORS["WHITE"]["name"]
SENSOR_COLOR_RED_NAME = COLORS["RED"]["name"]
SENSOR_COLOR_UNKNOWN_NAME = "inconnu"

HP_HOUR = 6
HC_HOUR = 22

# For forecast
DEVICE_MANUFACTURER = "RTE"
DEVICE_MODEL = "Calendrier Tempo"