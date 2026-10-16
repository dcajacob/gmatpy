"""The standard headless wheel includes all supported core workflows and SPICE."""
import json
import importlib
from pathlib import Path
import pytest
import gmatpy as g


def test_standard_package_supports_complete_headless_feature_set():
    info = g.capabilities()
    assert info.profile == "extended"  # Historical schema-1 metadata label.
    assert info.features == frozenset({
        "propagation", "state_conversion", "frame_conversion", "time_conversion",
        "native_de405", "native_session", "impulsive_maneuvers", "multi_spacecraft",
        "targeting", "mission_scripts", "spice_kernels",
    })
    assert not info.supports("estimation")
    assert not info.supports("gui")


def test_installed_build_inventory_contains_all_17_data_files():
    root = Path(g.__file__).resolve().parent
    if not (root / "BUILD_PROFILE.json").exists():
        pytest.skip("development overlay; installed inventory is tested in wheels")
    info = json.loads((root / "BUILD_PROFILE.json").read_text())
    assert info["schema_version"] == 1
    assert info["profile"] == "extended"
    assert info["spice"] is True
    actual = {p.relative_to(root / "data").as_posix()
              for p in (root / "data").rglob("*") if p.is_file()}
    assert actual == set(info["data_files"])
    assert len(actual) == 17
    assert "planetary_ephem/spk/gmatpy_de405_all_planets.bsp" in actual


@pytest.mark.parametrize("profile", ["minimal", "unknown"])
def test_obsolete_or_unknown_install_profile_is_rejected(tmp_path, monkeypatch, profile):
    module = importlib.import_module("gmatpy.capabilities")
    monkeypatch.setattr(module, "__file__", str(tmp_path / "capabilities.py"))
    (tmp_path / "BUILD_PROFILE.json").write_text(json.dumps({"profile": profile}))
    with pytest.raises(RuntimeError, match="standard full headless package"):
        module.capabilities()
