import pytest

from gmatpy import ForceModel, Spacecraft, propagate

STATE = [7000, 0, 0, 0, 7.5, 1]
EPOCH = "2020-07-20T12:00:00Z"


@pytest.mark.parametrize("kwargs", [
    {"state": [0]*6}, {"state": [1, 2]}, {"state": [7000, 0, 0, 0, float('nan'), 0]},
    {"state": [7000, 0, 0, 0, float('inf'), 0]}, {"epoch": "2020-07-20T12:00:00"},
    {"epoch": "garbage"}, {"times": [-1]}, {"times": [60, 30]}, {"times": [float('inf')]},
    {"max_step_s": 0}, {"accuracy": -1}, {"max_step_s": True},
])
def test_rejects_invalid_propagation_inputs(kwargs):
    params = dict(state=STATE, epoch=EPOCH, times=[0])
    params.update(kwargs)
    with pytest.raises(ValueError):
        propagate(**params)


@pytest.mark.parametrize("kwargs", [
    {"degree": -1}, {"degree": 361}, {"degree": 1.5}, {"degree": True},
    {"degree": 4, "order": 5}, {"gravity_model": "other"},
    {"gravity_model": "JGM3", "degree": 71}, {"sun": "false"}, {"f107": 0}, {"kp": 10},
])
def test_rejects_invalid_force_settings(kwargs):
    with pytest.raises(ValueError):
        ForceModel(**kwargs)


@pytest.mark.parametrize("kwargs", [{"mass_kg": 0}, {"drag_area_m2": -1}, {"cr": float('nan')}])
def test_rejects_invalid_spacecraft_settings(kwargs):
    with pytest.raises(ValueError):
        Spacecraft(**kwargs)


def test_empty_output_times():
    assert propagate(STATE, EPOCH, []) == []


def test_native_exception_is_a_python_exception_and_engine_recovers():
    from gmatpy import _runtime
    with _runtime.lock:
        gmat = _runtime.engine()
        gmat.Clear()
        try:
            gravity = gmat.Construct("GravityField", "InvalidGravity")
            with pytest.raises(gmat.APIException):
                gravity.SetField("Degree", -1)
        finally:
            gmat.Clear()
    assert len(propagate(STATE, EPOCH, [60])) == 1


def test_legacy_data_updater_is_disabled():
    from pathlib import Path
    from gmatpy import _runtime
    with _runtime.lock:
        gmat = _runtime.engine()
        directory = Path(gmat.FileManager.Instance().GetStartupFileDir())
        script = directory / "updateGmat.bat"
        marker = directory / "legacy-updater-ran"
        import shlex
        script.write_text(f"#!/bin/sh\ntouch {shlex.quote(str(marker))}\n", encoding="utf-8")
        script.chmod(0o755)
        try:
            assert gmat.Moderator.Instance().UpdateDataFiles() is False
            assert script.exists()
            assert not (directory / "updateGmat.bat.bak").exists()
            assert not marker.exists()
        finally:
            script.unlink(missing_ok=True)
            marker.unlink(missing_ok=True)
