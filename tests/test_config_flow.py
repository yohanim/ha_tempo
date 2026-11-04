"""Tests for config_flow: version constants and reconfigure step."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import OptionsFlowWithReload

from custom_components.tempo_rte_forecast.config_flow import (
    OptionsFlowHandler,
    TempoConfigFlow,
)


# ---------------------------------------------------------------------------
# Version constants
# ---------------------------------------------------------------------------


def test_config_flow_version_is_2() -> None:
    assert TempoConfigFlow.VERSION == 2


def test_config_flow_minor_version_is_1() -> None:
    assert TempoConfigFlow.MINOR_VERSION == 1


def test_async_get_options_flow_returns_handler() -> None:
    result = TempoConfigFlow.async_get_options_flow(MagicMock())
    assert isinstance(result, OptionsFlowHandler)


def test_options_flow_reloads_entry_on_save() -> None:
    """Saving options must reload the entry so coordinators pick them up."""
    assert issubclass(OptionsFlowHandler, OptionsFlowWithReload)
    assert OptionsFlowHandler.automatic_reload is True


# ---------------------------------------------------------------------------
# async_step_reconfigure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step_reconfigure_no_input_shows_form() -> None:
    """Without user_input, the step must show a form with step_id='reconfigure'."""
    flow = TempoConfigFlow.__new__(TempoConfigFlow)
    flow.async_show_form = MagicMock(return_value={"type": "form", "step_id": "reconfigure"})

    result = await flow.async_step_reconfigure(user_input=None)

    flow.async_show_form.assert_called_once()
    call_kwargs = flow.async_show_form.call_args
    assert call_kwargs.kwargs["step_id"] == "reconfigure"


@pytest.mark.asyncio
async def test_step_reconfigure_with_input_calls_abort() -> None:
    """Submitting the reconfigure form aborts with core's default reason (central translation)."""
    flow = TempoConfigFlow.__new__(TempoConfigFlow)
    mock_entry = MagicMock()
    flow._get_reconfigure_entry = MagicMock(return_value=mock_entry)
    flow.async_update_reload_and_abort = MagicMock(
        return_value={"type": "abort", "reason": "reconfigure_successful"}
    )

    result = await flow.async_step_reconfigure(user_input={})

    flow.async_update_reload_and_abort.assert_called_once_with(
        mock_entry
    )
    assert result["reason"] == "reconfigure_successful"


@pytest.mark.asyncio
async def test_step_reconfigure_empty_data_schema() -> None:
    """The reconfigure form schema must be empty (no configurable data fields)."""
    import voluptuous as vol

    flow = TempoConfigFlow.__new__(TempoConfigFlow)
    captured = {}

    def _capture_form(**kwargs):
        captured.update(kwargs)
        return {}

    flow.async_show_form = _capture_form

    await flow.async_step_reconfigure(user_input=None)

    assert captured.get("data_schema") == vol.Schema({})


# ---------------------------------------------------------------------------
# Off-peak ranges field visibility (HA 2026.11 conditional fields)
# ---------------------------------------------------------------------------


def test_offpeak_marker_falls_back_without_visible_support(monkeypatch) -> None:
    """On HA < 2026.11 the field is a plain vol.Optional, always shown."""
    import voluptuous as vol

    from custom_components.tempo_rte_forecast import config_flow
    from custom_components.tempo_rte_forecast.const import CONF_OFFPEAK_RANGES

    monkeypatch.setattr(config_flow, "_FlowOptional", None)
    marker = config_flow._offpeak_ranges_marker()
    assert type(marker) is vol.Optional
    assert marker.schema == CONF_OFFPEAK_RANGES
    assert getattr(marker, "visible", None) is None


def test_offpeak_marker_hidden_for_base_contract(monkeypatch) -> None:
    """On HA 2026.11+ the field is only visible for HC and Tempo contracts."""
    from custom_components.tempo_rte_forecast import config_flow
    from custom_components.tempo_rte_forecast.const import (
        CONF_CONTRACT,
        CONF_OFFPEAK_RANGES,
        CONTRACT_HEURES_CREUSES,
        CONTRACT_TEMPO,
    )

    class _FakeFlowOptional:
        def __init__(self, key, *, visible=None):
            self.schema = key
            self.visible = visible

    monkeypatch.setattr(config_flow, "_FlowOptional", _FakeFlowOptional)
    marker = config_flow._offpeak_ranges_marker()
    assert marker.schema == CONF_OFFPEAK_RANGES
    assert marker.visible == {
        "field": CONF_CONTRACT,
        "operator": "in",
        "value": [CONTRACT_HEURES_CREUSES, CONTRACT_TEMPO],
    }
