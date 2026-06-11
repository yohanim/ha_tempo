"""Tests for TempoDataCoordinator helper methods."""

from __future__ import annotations

from custom_components.tempo_rte_forecast.tempo_coordinator import TempoDataCoordinator


class TestDayNeedsCouleurTempoFill:
    def test_missing_day(self) -> None:
        assert TempoDataCoordinator._day_needs_couleur_tempo_fill({}, "2026-06-11") is True

    def test_valid_color(self) -> None:
        values = {"2026-06-11": "blue"}
        assert TempoDataCoordinator._day_needs_couleur_tempo_fill(values, "2026-06-11") is False

    def test_unknown_string(self) -> None:
        values = {"2026-06-11": "unknown"}
        assert TempoDataCoordinator._day_needs_couleur_tempo_fill(values, "2026-06-11") is True

    def test_non_string_value(self) -> None:
        values = {"2026-06-11": 1}
        assert TempoDataCoordinator._day_needs_couleur_tempo_fill(values, "2026-06-11") is True


class TestCouleurTempoPayloadToColorKey:
    def test_code_mapping(self) -> None:
        assert TempoDataCoordinator._couleur_tempo_payload_to_color_key({"codeJour": 1}) == "blue"
        assert TempoDataCoordinator._couleur_tempo_payload_to_color_key({"codeJour": 2}) == "white"
        assert TempoDataCoordinator._couleur_tempo_payload_to_color_key({"codeJour": 3}) == "red"

    def test_code_zero_is_unavailable(self) -> None:
        assert TempoDataCoordinator._couleur_tempo_payload_to_color_key({"codeJour": 0}) is None

    def test_lib_couleur_fallback(self) -> None:
        payload = {"codeJour": 99, "libCouleur": "Rouge"}
        assert TempoDataCoordinator._couleur_tempo_payload_to_color_key(payload) == "red"

    def test_empty_payload(self) -> None:
        assert TempoDataCoordinator._couleur_tempo_payload_to_color_key(None) is None
