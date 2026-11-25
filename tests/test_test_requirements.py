"""scripts/test_requirements.py: versions of the CI "minimum" and "latest" runs."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HACS = REPO_ROOT / "hacs.json"
MANIFEST = REPO_ROOT / "custom_components" / "tempo_rte_forecast" / "manifest.json"


def _module():
    path = REPO_ROOT / "scripts" / "test_requirements.py"
    spec = importlib.util.spec_from_file_location("test_requirements_script", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize(
    ("requirement", "expected"),
    [
        ("babel>=2.18", "babel==2.18"),
        ("babel", "babel"),  # no floor: kept as declared
        ("pkg>=1.0,<2", "pkg>=1.0,<2"),  # bounded range: kept as declared
    ],
)
def test_pin_to_minimum(requirement: str, expected: str) -> None:
    assert _module().pin_to_minimum(requirement) == expected


def test_minimum_run_follows_hacs_floor() -> None:
    mod = _module()
    floor = json.loads(HACS.read_text(encoding="utf-8"))["homeassistant"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert mod.requirements("minimum") == [
        f"pytest-homeassistant=={floor}",
        *(mod.pin_to_minimum(r) for r in manifest["requirements"]),
    ]


def test_latest_run_is_unpinned() -> None:
    mod = _module()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert mod.requirements("latest") == ["pytest-homeassistant", *manifest["requirements"]]
