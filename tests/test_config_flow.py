"""Tests for config_flow: version constants and reconfigure step."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

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
    """Submitting the reconfigure form must abort with reason 'reconfigure_successful'."""
    flow = TempoConfigFlow.__new__(TempoConfigFlow)
    mock_entry = MagicMock()
    flow._get_reconfigure_entry = MagicMock(return_value=mock_entry)
    flow.async_update_reload_and_abort = MagicMock(
        return_value={"type": "abort", "reason": "reconfigure_successful"}
    )

    result = await flow.async_step_reconfigure(user_input={})

    flow.async_update_reload_and_abort.assert_called_once_with(
        mock_entry, reason="reconfigure_successful"
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
