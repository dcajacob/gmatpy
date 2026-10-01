"""Numerical checks exercised against an installed wheel, not source-path imports."""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor
import math
import multiprocessing
from pathlib import Path
import os
import subprocess
import sys

import pytest

from gmat_hpop import ForceModel, Spacecraft, propagate

EPOCH = "2020-07-20T12:00:00Z"
MU = 398600.4415  # GMAT's default Earth gravitational parameter, km^3/s^2.
RADIUS = 7000.0
SPEED = math.sqrt(MU / RADIUS)
INITIAL = (RADIUS, 0, 0, 0, SPEED, 0)
TWO_BODY = ForceModel(degree=0, sun=False, moon=False, srp=False)


def _spawned_orbit(radius):
    initial = (radius, 0, 0, 0, math.sqrt(MU / radius), 0)
    return propagate(initial, EPOCH, [60], forces=TWO_BODY)[0]


def test_circular_orbit_against_analytic_solution():
    period = 2 * math.pi * math.sqrt(RADIUS**3 / MU)
    times = [0, 0, period / 4, period / 2, period]
    samples = propagate(INITIAL, EPOCH, times, forces=TWO_BODY)
    for sample, time in zip(samples, times):
        angle = SPEED / RADIUS * time
        expected = (RADIUS * math.cos(angle), RADIUS * math.sin(angle), 0,
                    -SPEED * math.sin(angle), SPEED * math.cos(angle), 0)
        assert sample.time_s == time
        assert sample.position_km == pytest.approx(expected[:3], abs=2e-6)
        assert sample.velocity_km_s == pytest.approx(expected[3:], abs=2e-9)
        r = math.hypot(*sample.position_km)
        v2 = sum(v*v for v in sample.velocity_km_s)
        assert v2 / 2 - MU / r == pytest.approx(-MU / (2 * RADIUS), abs=1e-9)
    assert samples[0] == samples[1]


def test_matches_gmat_published_jgm3_example():
    # Independent native setup from application/api/Ex_R2020a_BasicFM.py and
    # Ex_R2020a_PropagationStep.py. Use Keplerian input to catch Cartesian facade
    # setup errors; compare states before/after its published 60-second step.
    from gmat_hpop import _runtime
    with _runtime.lock:
        gmat = _runtime.engine()
        gmat.Clear()
        try:
            sat = gmat.Construct("Spacecraft", "EarthOrbiter")
            sat.SetField("DateFormat", "UTCGregorian")
            sat.SetField("Epoch", "20 Jul 2020 12:00:00.000")
            sat.SetField("CoordinateSystem", "EarthMJ2000Eq")
            sat.SetField("DisplayStateType", "Keplerian")
            for key, value in zip(("SMA", "ECC", "INC", "RAAN", "AOP", "TA"),
                                  (6600, 0.05, 78, 45, 90, 180)):
                sat.SetField(key, value)
            fm = gmat.Construct("ForceModel", "FM")
            fm.SetField("CentralBody", "Earth")
            gravity = gmat.Construct("GravityField", "Earth8x8")
            gravity.SetField("BodyName", "Earth")
            gravity.SetField("PotentialFile", str(Path(_runtime.__file__).parent /
                              "data/gravity/earth/JGM3.cof"))
            gravity.SetField("Degree", 8)
            gravity.SetField("Order", 8)
            fm.AddForce(gravity)
            prop = gmat.Construct("Propagator", "PDProp")
            prop.SetReference(gmat.Construct("PrinceDormand78", "Gator"))
            prop.SetReference(fm)
            prop.SetField("InitialStepSize", 60.0)
            prop.SetField("Accuracy", 1e-12)
            prop.SetField("MinStep", 0.0)
            gmat.Initialize()
            prop.AddPropObject(sat)
            prop.PrepareInternals()
            integrator = prop.GetPropagator()
            initial = tuple(integrator.GetState())
            assert integrator.Step(60.0)
            expected = tuple(integrator.GetState())
        finally:
            gmat.Clear()
    samples = propagate(initial, EPOCH, [0, 60],
                        forces=ForceModel(gravity_model="JGM3", sun=False, moon=False, srp=False))
    assert samples[0].state == pytest.approx(initial, abs=1e-12)
    assert samples[1].state == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize("forces", [
    ForceModel(degree=8, sun=False, moon=False, srp=False),
    ForceModel(degree=70, sun=False, moon=False, srp=False),
    ForceModel(degree=0, sun=True, moon=False, srp=False),
    ForceModel(degree=0, sun=False, moon=True, srp=False),
    ForceModel(degree=0, sun=False, moon=False, srp=True),
    ForceModel(degree=0, sun=False, moon=False, srp=False, drag=True),
])
def test_each_perturbation_changes_the_trajectory(forces):
    sat = Spacecraft(mass_kg=100, srp_area_m2=20, drag_area_m2=20)
    reference = propagate(INITIAL, EPOCH, [3600], forces=TWO_BODY, spacecraft=sat)[0]
    perturbed = propagate(INITIAL, EPOCH, [3600], forces=forces, spacecraft=sat)[0]
    assert math.dist(reference.position_km, perturbed.position_km) > 1e-7


def test_repeat_calls_and_threads_do_not_share_orbit_state():
    def run(radius):
        initial = (radius, 0, 0, 0, math.sqrt(MU / radius), 0)
        return propagate(initial, EPOCH, [0, 600], forces=TWO_BODY)
    expected = [run(7000), run(8000)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(run, [7000, 8000])) == expected
    assert run(7000) == expected[0]


def test_timezone_offsets_and_fractional_output_times():
    expected = propagate(INITIAL, EPOCH, [0, 0.01, 10.123], forces=TWO_BODY)
    actual = propagate(INITIAL, "2020-07-20T06:00:00-06:00", [0, 0.01, 10.123], forces=TWO_BODY)
    assert actual == expected


def test_spawned_processes_have_independent_engines():
    expected = [_spawned_orbit(radius) for radius in (7000, 8000)]
    with ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context("spawn")) as pool:
        assert list(pool.map(_spawned_orbit, (7000, 8000))) == expected


def test_full_egm96_field():
    sample = propagate(INITIAL, EPOCH, [60],
                       forces=ForceModel(degree=360, sun=False, moon=False, srp=False))[0]
    assert 6900 < math.hypot(*sample.position_km) < 7100


def test_runs_without_display_and_preserves_cwd(tmp_path):
    code = """
from pathlib import Path
from gmat_hpop import propagate
cwd = Path.cwd()
result = propagate([7000,0,0,0,7.5,1], '2020-07-20T12:00:00Z', [0,60])
assert len(result) == 2
assert cwd == Path.cwd()
assert list(cwd.iterdir()) == []
print('HEADLESS_OK')
"""
    env = {k: v for k, v in os.environ.items()
           if k not in ("DISPLAY", "WAYLAND_DISPLAY", "PYTHONPATH", "LD_LIBRARY_PATH", "GMAT")}
    result = subprocess.run([sys.executable, "-I", "-c", code], cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "HEADLESS_OK" in result.stdout


def test_fork_is_rejected_before_acquiring_inherited_lock():
    if not hasattr(os, "fork"):
        pytest.skip("fork unavailable")
    from gmat_hpop import _runtime
    with _runtime.lock:
        child = os.fork()
        if child == 0:
            try:
                propagate(INITIAL, EPOCH, [60])
            except RuntimeError as error:
                os._exit(0 if "spawn" in str(error) else 1)
            except BaseException:
                os._exit(2)
            os._exit(3)
        _, status = os.waitpid(child, 0)
    assert os.waitstatus_to_exitcode(status) == 0
