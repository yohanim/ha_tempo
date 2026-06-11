"""Tests for __init__.py: PLATFORMS constant and async_migrate_entry."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.const import Platform

from custom_components.tempo_rte_forecast import PLATFORMS, async_migrate_entry
from custom_components.tempo_rte_forecast.const import DOMAIN


# ---------------------------------------------------------------------------
# PLATFORMS
# ---------------------------------------------------------------------------


def test_platforms_uses_platform_enum() -> None:
    """PLATFORMS must contain the enum value, not the bare string."""
    assert PLATFORMS == [Platform.SENSOR]
    assert all(isinstance(p, Platform) for p in PLATFORMS)


# ---------------------------------------------------------------------------
# async_migrate_entry — helpers
# ---------------------------------------------------------------------------


def _make_entity(unique_id: str, entity_id: str) -> MagicMock:
    e = MagicMock()
    e.unique_id = unique_id
    e.domain = "sensor"
    e.platform = DOMAIN
    e.entity_id = entity_id
    return e


def _run_migration(entities: list, entry_id: str = "abc123") -> tuple[MagicMock, MagicMock]:
    """Run async_migrate_entry with a v1 entry and return (hass, ent_reg) mocks."""
    hass = MagicMock()
    entry = MagicMock()
    entry.version = 1
    entry.entry_id = entry_id

    mock_ent_reg = MagicMock()
    mock_ent_reg.async_get_entity_id.return_value = None  # new ID is free

    with (
        patch("custom_components.tempo_rte_forecast.er.async_get", return_value=mock_ent_reg),
        patch(
            "custom_components.tempo_rte_forecast.er.async_entries_for_config_entry",
            return_value=entities,
        ),
    ):
        import asyncio

        asyncio.get_event_loop().run_until_complete(async_migrate_entry(hass, entry))

    return hass, mock_ent_reg


# ---------------------------------------------------------------------------
# async_migrate_entry tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_migrate_entry_returns_true_for_v1() -> None:
    """Function must return True so HA considers the migration successful."""
    hass = MagicMock()
    entry = MagicMock()
    entry.version = 1
    entry.entry_id = "abc123"

    with (
        patch("custom_components.tempo_rte_forecast.er.async_get", return_value=MagicMock()),
        patch(
            "custom_components.tempo_rte_forecast.er.async_entries_for_config_entry",
            return_value=[],
        ),
    ):
        result = await async_migrate_entry(hass, entry)

    assert result is True


@pytest.mark.asyncio
async def test_migrate_entry_returns_true_for_v2() -> None:
    """v2 entries must also return True without touching the registry."""
    hass = MagicMock()
    entry = MagicMock()
    entry.version = 2

    with patch("custom_components.tempo_rte_forecast.er.async_get") as mock_er_get:
        result = await async_migrate_entry(hass, entry)

    assert result is True
    mock_er_get.assert_not_called()


@pytest.mark.asyncio
async def test_migrate_entry_v2_skips_version_bump() -> None:
    """v2 entries must not trigger async_update_entry."""
    hass = MagicMock()
    entry = MagicMock()
    entry.version = 2

    with patch("custom_components.tempo_rte_forecast.er.async_get"):
        await async_migrate_entry(hass, entry)

    hass.config_entries.async_update_entry.assert_not_called()


@pytest.mark.asyncio
async def test_migrate_entry_bumps_version_to_2() -> None:
    """v1 entries must be bumped to version 2."""
    hass = MagicMock()
    entry = MagicMock()
    entry.version = 1
    entry.entry_id = "abc123"

    with (
        patch("custom_components.tempo_rte_forecast.er.async_get", return_value=MagicMock()),
        patch(
            "custom_components.tempo_rte_forecast.er.async_entries_for_config_entry",
            return_value=[],
        ),
    ):
        await async_migrate_entry(hass, entry)

    hass.config_entries.async_update_entry.assert_called_once_with(entry, version=2)


@pytest.mark.asyncio
async def test_migrate_entry_renames_j_unique_id() -> None:
    """tempo_rte_forecast_J → entry_id_J."""
    hass = MagicMock()
    entry = MagicMock()
    entry.version = 1
    entry.entry_id = "abc123"

    entity = _make_entity(f"{DOMAIN}_J", "sensor.tempo_color_j")
    mock_ent_reg = MagicMock()
    mock_ent_reg.async_get_entity_id.return_value = None

    with (
        patch("custom_components.tempo_rte_forecast.er.async_get", return_value=mock_ent_reg),
        patch(
            "custom_components.tempo_rte_forecast.er.async_entries_for_config_entry",
            return_value=[entity],
        ),
    ):
        await async_migrate_entry(hass, entry)

    mock_ent_reg.async_update_entity.assert_called_once_with(
        "sensor.tempo_color_j", new_unique_id="abc123_J"
    )


@pytest.mark.asyncio
async def test_migrate_entry_renames_current_price_unique_id() -> None:
    """tempo_rte_forecast_current_price → entry_id_current_price."""
    hass = MagicMock()
    entry = MagicMock()
    entry.version = 1
    entry.entry_id = "abc123"

    entity = _make_entity(f"{DOMAIN}_current_price", "sensor.current_price")
    mock_ent_reg = MagicMock()
    mock_ent_reg.async_get_entity_id.return_value = None

    with (
        patch("custom_components.tempo_rte_forecast.er.async_get", return_value=mock_ent_reg),
        patch(
            "custom_components.tempo_rte_forecast.er.async_entries_for_config_entry",
            return_value=[entity],
        ),
    ):
        await async_migrate_entry(hass, entry)

    mock_ent_reg.async_update_entity.assert_called_once_with(
        "sensor.current_price", new_unique_id="abc123_current_price"
    )


@pytest.mark.asyncio
async def test_migrate_entry_renames_tempo_price_unique_id() -> None:
    """tempo_rte_forecast_tempo_blue_hp → entry_id_tempo_blue_hp."""
    hass = MagicMock()
    entry = MagicMock()
    entry.version = 1
    entry.entry_id = "abc123"

    entity = _make_entity(f"{DOMAIN}_tempo_blue_hp", "sensor.price_tempo_blue_hp")
    mock_ent_reg = MagicMock()
    mock_ent_reg.async_get_entity_id.return_value = None

    with (
        patch("custom_components.tempo_rte_forecast.er.async_get", return_value=mock_ent_reg),
        patch(
            "custom_components.tempo_rte_forecast.er.async_entries_for_config_entry",
            return_value=[entity],
        ),
    ):
        await async_migrate_entry(hass, entry)

    mock_ent_reg.async_update_entity.assert_called_once_with(
        "sensor.price_tempo_blue_hp", new_unique_id="abc123_tempo_blue_hp"
    )


@pytest.mark.asyncio
async def test_migrate_entry_skips_rename_if_new_id_already_exists() -> None:
    """If the target unique ID is already taken, do not overwrite it."""
    hass = MagicMock()
    entry = MagicMock()
    entry.version = 1
    entry.entry_id = "abc123"

    entity = _make_entity(f"{DOMAIN}_J", "sensor.tempo_color_j")
    mock_ent_reg = MagicMock()
    # Simulate collision: new unique ID already registered
    mock_ent_reg.async_get_entity_id.return_value = "sensor.tempo_color_j_duplicate"

    with (
        patch("custom_components.tempo_rte_forecast.er.async_get", return_value=mock_ent_reg),
        patch(
            "custom_components.tempo_rte_forecast.er.async_entries_for_config_entry",
            return_value=[entity],
        ),
    ):
        await async_migrate_entry(hass, entry)

    mock_ent_reg.async_update_entity.assert_not_called()


@pytest.mark.asyncio
async def test_migrate_entry_ignores_already_migrated_unique_id() -> None:
    """Entities with entry_id-based unique IDs must not be renamed."""
    hass = MagicMock()
    entry = MagicMock()
    entry.version = 1
    entry.entry_id = "abc123"

    # Already migrated format — should produce no update call
    entity = _make_entity("abc123_J", "sensor.tempo_color_j")
    mock_ent_reg = MagicMock()
    mock_ent_reg.async_get_entity_id.return_value = None

    with (
        patch("custom_components.tempo_rte_forecast.er.async_get", return_value=mock_ent_reg),
        patch(
            "custom_components.tempo_rte_forecast.er.async_entries_for_config_entry",
            return_value=[entity],
        ),
    ):
        await async_migrate_entry(hass, entry)

    mock_ent_reg.async_update_entity.assert_not_called()
