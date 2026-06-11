"""Tests for coordinator retry mixin helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.tempo_rte_forecast.coordinator_retry import (
    _coordinator_wrap_handle_refresh,
)


def test_coordinator_wrap_handle_refresh_uses_private_method() -> None:
    """Ensure name mangling does not break refresh callback lookup."""
    expected = MagicMock()
    coordinator = MagicMock()
    coordinator._DataUpdateCoordinator__wrap_handle_refresh_interval = expected

    assert _coordinator_wrap_handle_refresh(coordinator) is expected
