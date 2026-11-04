"""Child devices layout, off-peak validation and repair issues."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from homeassistant import loader
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_test_home_assistant,
)

from custom_components.tempo_rte_forecast import config_flow
from custom_components.tempo_rte_forecast.const import (
    CONF_CONTRACT,
    CONF_OFFPEAK_RANGES,
    CONTRACT_BASE,
    CONTRACT_HEURES_CREUSES,
    CONTRACT_TEMPO,
    DOMAIN,
)
from custom_components.tempo_rte_forecast.issues import (
    API_OUTAGE_THRESHOLD,
    ISSUE_INVALID_OFFPEAK,
    api_issue_id,
    async_check_offpeak_ranges,
    async_track_api_outage,
)
from custom_components.tempo_rte_forecast.utils import invalid_offpeak_parts


# ---------------------------------------------------------------------------
# invalid_offpeak_parts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, []),
        ("", []),
        ("22:00-06:00", []),
        ("22:00-06:00, 12:00-14:00", []),
        ("22:00-06:00,,", []),
        ("22h-6h", ["22h-6h"]),
        ("22:00-06:00, 25:00-26:00", ["25:00-26:00"]),
        ("22:00", ["22:00"]),
        ("1-2-3", ["1-2-3"]),
    ],
)
def test_invalid_offpeak_parts(value, expected) -> None:
    assert invalid_offpeak_parts(value) == expected


# ---------------------------------------------------------------------------
# Options flow: off-peak validation
# ---------------------------------------------------------------------------


def _prices_flow(data: dict) -> config_flow.OptionsFlowHandler:
    flow = config_flow.OptionsFlowHandler()
    flow._data = dict(data)
    flow.async_step_init = AsyncMock(return_value={"type": "menu"})
    return flow


async def test_prices_rejects_invalid_offpeak_and_keeps_input() -> None:
    flow = _prices_flow({CONF_CONTRACT: CONTRACT_TEMPO})
    user_input = {CONF_CONTRACT: CONTRACT_HEURES_CREUSES, CONF_OFFPEAK_RANGES: "22h-6h"}

    result = await flow.async_step_prices(user_input)

    assert result["type"] == "form"
    assert result["errors"] == {CONF_OFFPEAK_RANGES: "invalid_offpeak_ranges"}
    assert CONF_OFFPEAK_RANGES not in flow._data
    flow.async_step_init.assert_not_called()
    suggested = {
        key.schema: key.description["suggested_value"]
        for key in result["data_schema"].schema
        if key.description
    }
    assert suggested[CONF_OFFPEAK_RANGES] == "22h-6h"
    assert suggested[CONF_CONTRACT] == CONTRACT_HEURES_CREUSES


async def test_prices_accepts_valid_offpeak() -> None:
    flow = _prices_flow({})
    user_input = {CONF_CONTRACT: CONTRACT_TEMPO, CONF_OFFPEAK_RANGES: "22:00-06:00"}

    await flow.async_step_prices(user_input)

    assert flow._data[CONF_OFFPEAK_RANGES] == "22:00-06:00"
    flow.async_step_init.assert_awaited_once()


async def test_prices_base_contract_ignores_offpeak_format() -> None:
    """Base has no off-peak hours; the (hidden) field is not validated."""
    flow = _prices_flow({})

    await flow.async_step_prices({CONF_CONTRACT: CONTRACT_BASE, CONF_OFFPEAK_RANGES: "junk"})

    flow.async_step_init.assert_awaited_once()


# ---------------------------------------------------------------------------
# Repair issues
# ---------------------------------------------------------------------------


@pytest.fixture
async def issue_hass(hass: HomeAssistant) -> HomeAssistant:
    await ir.async_load(hass)
    return hass


def _issue(hass: HomeAssistant, issue_id: str):
    return ir.async_get(hass).async_get_issue(DOMAIN, issue_id)


async def test_api_outage_issue_after_threshold_and_cleared(issue_hass) -> None:
    hass = issue_hass
    coordinator = MagicMock()
    coordinator.last_update_success = False
    listeners = []
    coordinator.async_add_listener = lambda cb: listeners.append(cb) or (lambda: None)

    start = dt_util.utcnow()
    with patch("custom_components.tempo_rte_forecast.issues.dt_util.utcnow", return_value=start):
        async_track_api_outage(hass, coordinator, "rte", "RTE")
    assert _issue(hass, api_issue_id("rte")) is None

    # Still failing, but before the threshold: no issue.
    with patch(
        "custom_components.tempo_rte_forecast.issues.dt_util.utcnow",
        return_value=start + API_OUTAGE_THRESHOLD - timedelta(minutes=1),
    ):
        listeners[0]()
    assert _issue(hass, api_issue_id("rte")) is None

    with patch(
        "custom_components.tempo_rte_forecast.issues.dt_util.utcnow",
        return_value=start + API_OUTAGE_THRESHOLD,
    ):
        listeners[0]()
    issue = _issue(hass, api_issue_id("rte"))
    assert issue is not None
    assert issue.translation_key == "api_unavailable"
    assert issue.translation_placeholders == {"api": "RTE", "hours": "24"}

    coordinator.last_update_success = True
    listeners[0]()
    assert _issue(hass, api_issue_id("rte")) is None


async def test_api_outage_clock_resets_after_success(issue_hass) -> None:
    hass = issue_hass
    coordinator = MagicMock()
    coordinator.last_update_success = False
    listeners = []
    coordinator.async_add_listener = lambda cb: listeners.append(cb) or (lambda: None)
    start = dt_util.utcnow()
    target = "custom_components.tempo_rte_forecast.issues.dt_util.utcnow"

    with patch(target, return_value=start):
        async_track_api_outage(hass, coordinator, "opendpe", "Open DPE")
    coordinator.last_update_success = True
    with patch(target, return_value=start + timedelta(hours=1)):
        listeners[0]()
    coordinator.last_update_success = False
    with patch(target, return_value=start + API_OUTAGE_THRESHOLD + timedelta(minutes=1)):
        listeners[0]()

    assert _issue(hass, api_issue_id("opendpe")) is None


@pytest.mark.parametrize(
    ("options", "expected_issue"),
    [
        ({CONF_CONTRACT: CONTRACT_TEMPO, CONF_OFFPEAK_RANGES: "22h-6h"}, True),
        ({CONF_CONTRACT: CONTRACT_HEURES_CREUSES, CONF_OFFPEAK_RANGES: "22:00-06:00"}, False),
        ({CONF_CONTRACT: CONTRACT_BASE, CONF_OFFPEAK_RANGES: "22h-6h"}, False),
    ],
)
async def test_offpeak_issue(issue_hass, options, expected_issue) -> None:
    entry = MagicMock()
    entry.options = options

    async_check_offpeak_ranges(issue_hass, entry)

    issue = _issue(issue_hass, ISSUE_INVALID_OFFPEAK)
    assert (issue is not None) is expected_issue
    if expected_issue:
        assert issue.translation_placeholders == {"ranges": "22h-6h"}


async def test_offpeak_issue_cleared_once_fixed(issue_hass) -> None:
    entry = MagicMock()
    entry.options = {CONF_CONTRACT: CONTRACT_TEMPO, CONF_OFFPEAK_RANGES: "bad"}
    async_check_offpeak_ranges(issue_hass, entry)
    assert _issue(issue_hass, ISSUE_INVALID_OFFPEAK) is not None

    entry.options = {CONF_CONTRACT: CONTRACT_TEMPO, CONF_OFFPEAK_RANGES: "22:00-06:00"}
    async_check_offpeak_ranges(issue_hass, entry)
    assert _issue(issue_hass, ISSUE_INVALID_OFFPEAK) is None


# ---------------------------------------------------------------------------
# Full setup: main device + child devices
# ---------------------------------------------------------------------------


@pytest.fixture
async def full_hass():
    """Full test instance (config entries, registries) with custom integrations."""
    async with async_test_home_assistant() as hass:
        hass.data.pop(loader.DATA_CUSTOM_COMPONENTS, None)
        yield hass


async def test_setup_creates_main_and_child_devices(full_hass: HomeAssistant) -> None:
    hass = full_hass
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id=DOMAIN,
        options={CONF_CONTRACT: CONTRACT_TEMPO, CONF_OFFPEAK_RANGES: "22:00-06:00"},
    )
    entry.add_to_hass(hass)

    pkg = "custom_components.tempo_rte_forecast"
    with (
        patch(f"{pkg}.tempo_coordinator.TempoDataCoordinator._async_update_data", AsyncMock(return_value={})),
        patch(f"{pkg}.forecast_coordinator.ForecastCoordinator._async_update_data", AsyncMock(return_value=[])),
        patch(f"{pkg}.prices_coordinator.PriceCoordinator._async_update_data", AsyncMock(return_value={})),
        patch(f"{pkg}.prices_coordinator.PriceCoordinator.async_schedule_initial_fetch"),
        patch(f"{pkg}.tempo_coordinator.async_get_clientsession"),
        patch(f"{pkg}.forecast_coordinator.async_get_clientsession"),
        patch(f"{pkg}.prices_coordinator.async_get_clientsession"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    mains = dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
    assert len(mains) == 1
    main = mains[0]
    assert main.identifiers == {(DOMAIN, entry.entry_id)}
    devices = {
        ident: device
        for device in dr.async_entries_for_parent_device(dev_reg, main.id)
        for (_, ident) in device.identifiers
    }
    assert set(devices) == {f"{entry.entry_id}_forecast", f"{entry.entry_id}_prices"}
    forecast = devices[f"{entry.entry_id}_forecast"]
    prices = devices[f"{entry.entry_id}_prices"]
    assert getattr(main, "parent_device_id", None) is None
    assert forecast.name == "Open DPE forecast"
    assert prices.name == "Electricity prices"

    assert forecast.parent_device_id == main.id
    assert prices.parent_device_id == main.id
    assert entry.runtime_data.main_device_id == main.id

    def device_of(unique_id: str) -> str | None:
        entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id is not None, unique_id
        return ent_reg.async_get(entity_id).device_id

    assert device_of(f"{entry.entry_id}_J") == main.id
    assert device_of(f"{entry.entry_id}_J+1") == main.id
    assert device_of(f"{entry.entry_id}_J1_combined") == main.id
    assert device_of(f"{entry.entry_id}_forecast_opendpe_j1") == forecast.id
    assert device_of(f"{entry.entry_id}_current_price") == prices.id

    assert await hass.config_entries.async_unload(entry.entry_id)
