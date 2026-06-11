"""Ensure translation files stay aligned with code and each other."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from custom_components.tempo_rte_forecast.const import (
    CONF_CONTRACT,
    CONF_EDF_TEMPO_COLOR_REFRESH_TIME,
    CONF_FORECAST_RETRY_DELAY,
    CONF_ICON_COLOR_BLUE,
    CONF_ICON_COLOR_RED,
    CONF_ICON_COLOR_UNKNOWN,
    CONF_ICON_COLOR_WHITE,
    CONF_OFFPEAK_RANGES,
    CONF_OPENDPE_SERVICE_TYPE,
    CONF_PRICE_UPDATE_INTERVAL,
    CONF_RTE_TEMPO_COLOR_REFRESH_TIME,
    CONF_SUBSCRIBED_POWER,
    CONF_TEMPO_DAY_CHANGE_TIME,
    CONF_TEMPO_RETRY_DELAY,
    CONTRACT_BASE,
    CONTRACT_HEURES_CREUSES,
    CONTRACT_TEMPO,
    OPENDPE_SERVICE_FULL,
    OPENDPE_SERVICE_LIGHT,
)
from custom_components.tempo_rte_forecast.utils import localized_color_label

INTEGRATION_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "tempo_rte_forecast"
STRINGS_PATH = INTEGRATION_DIR / "strings.json"
TRANSLATIONS_DIR = INTEGRATION_DIR / "translations"

ENTITY_TRANSLATION_KEYS = {
    "tempo_color",
    "tempo_color_j1",
    "tempo_combined",
    "tempo_forecast",
    "price",
    "specific_price",
}

ENTITY_STATE_KEYS = {"blue", "white", "red", "unknown"}

SELECTOR_TRANSLATION_KEYS = {"contract", "opendpe_service_type"}

OPTION_DATA_KEYS = {
    CONF_CONTRACT,
    CONF_SUBSCRIBED_POWER,
    CONF_OFFPEAK_RANGES,
    CONF_PRICE_UPDATE_INTERVAL,
    CONF_TEMPO_DAY_CHANGE_TIME,
    CONF_RTE_TEMPO_COLOR_REFRESH_TIME,
    CONF_EDF_TEMPO_COLOR_REFRESH_TIME,
    CONF_OPENDPE_SERVICE_TYPE,
    CONF_TEMPO_RETRY_DELAY,
    CONF_FORECAST_RETRY_DELAY,
    CONF_ICON_COLOR_BLUE,
    CONF_ICON_COLOR_WHITE,
    CONF_ICON_COLOR_RED,
    CONF_ICON_COLOR_UNKNOWN,
}

MENU_OPTION_KEYS = {"prices", "api", "retries", "icons", "finish"}

VALID_SELECTOR_KEY = re.compile(r"^[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?$")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _leaf_keys(obj: object, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            keys.add(path)
            keys.update(_leaf_keys(value, path))
    return keys


@pytest.fixture
def strings() -> dict:
    return _load_json(STRINGS_PATH)


@pytest.fixture
def fr_strings() -> dict:
    return _load_json(TRANSLATIONS_DIR / "fr.json")


def test_translation_files_exist() -> None:
    assert STRINGS_PATH.is_file()
    assert (TRANSLATIONS_DIR / "fr.json").is_file()


def test_fr_matches_strings_structure(strings: dict, fr_strings: dict) -> None:
    assert _leaf_keys(strings) == _leaf_keys(fr_strings)


def test_selector_keys_are_valid_slug(strings: dict) -> None:
    for selector_name, selector_def in strings["selector"].items():
        assert selector_name in SELECTOR_TRANSLATION_KEYS
        for option_key in selector_def["options"]:
            assert VALID_SELECTOR_KEY.match(option_key), option_key


def test_selector_contract_matches_code(strings: dict, fr_strings: dict) -> None:
    expected = {CONTRACT_BASE, CONTRACT_HEURES_CREUSES, CONTRACT_TEMPO}
    assert set(strings["selector"]["contract"]["options"]) == expected
    assert set(fr_strings["selector"]["contract"]["options"]) == expected


def test_selector_opendpe_matches_code(strings: dict, fr_strings: dict) -> None:
    expected = {OPENDPE_SERVICE_LIGHT, OPENDPE_SERVICE_FULL}
    assert set(strings["selector"]["opendpe_service_type"]["options"]) == expected
    assert set(fr_strings["selector"]["opendpe_service_type"]["options"]) == expected


def test_options_data_keys_match_conf_constants(strings: dict, fr_strings: dict) -> None:
    data_keys = set()
    for step in strings["options"]["step"].values():
        if "data" in step:
            data_keys.update(step["data"])
    assert data_keys == OPTION_DATA_KEYS
    assert set(fr_strings["options"]["step"]["prices"]["data"]) <= OPTION_DATA_KEYS


def test_options_menu_keys(strings: dict, fr_strings: dict) -> None:
    menu_keys = set(strings["options"]["step"]["init"]["menu_options"])
    assert menu_keys == MENU_OPTION_KEYS
    assert set(fr_strings["options"]["step"]["init"]["menu_options"]) == MENU_OPTION_KEYS


def test_entity_translation_keys(strings: dict, fr_strings: dict) -> None:
    sensor_keys = set(strings["entity"]["sensor"])
    assert sensor_keys == ENTITY_TRANSLATION_KEYS
    assert set(fr_strings["entity"]["sensor"]) == ENTITY_TRANSLATION_KEYS


def test_entity_state_keys(strings: dict, fr_strings: dict) -> None:
    for key in ("tempo_color", "tempo_color_j1", "tempo_combined", "tempo_forecast"):
        assert set(strings["entity"]["sensor"][key]["state"]) == ENTITY_STATE_KEYS
        assert set(fr_strings["entity"]["sensor"][key]["state"]) == ENTITY_STATE_KEYS


def test_services_refresh_key(strings: dict, fr_strings: dict) -> None:
    assert "refresh" in strings["services"]
    assert set(strings["services"]) == set(fr_strings["services"])


def test_localized_color_label_fr_and_en() -> None:
    assert localized_color_label("blue", "fr") == "Bleu"
    assert localized_color_label("blue", "en") == "blue"
