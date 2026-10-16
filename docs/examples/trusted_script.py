"""Run the accompanying trusted finite-burn script and copy its outputs."""

import math
from pathlib import Path
import tempfile

import gmatpy as gmat

if not gmat.capabilities().supports("mission_scripts"):
    # The nonexistent path must not be examined before the capability check.
    try:
        gmat.run_script("does-not-exist.script", outputs={})
    except gmat.UnsupportedCapabilityError:
        pass
    else:
        raise AssertionError("Expected an early extended-profile capability error")
    print("SKIP: trusted_script.py requires the extended profile")
    raise SystemExit(0)

# Resolve bundled data from the installed package, never a local GMAT checkout.
gravity_file = Path(gmat.__file__).resolve().parent / "data/gravity/earth/EGM96.cof"
template = Path(__file__).with_name("finite_burn.script").read_text(encoding="utf-8")
fields = ["X", "Y", "Z", "VX", "VY", "VZ", "TotalMass"]
with tempfile.TemporaryDirectory(prefix="gmatpy-example-") as directory:
    script = Path(directory) / "finite_burn.script"
    script.write_text(template.replace("__GMATPY_EGM96__", gravity_file.as_posix()),
                      encoding="utf-8")
    copied = gmat.run_script(script, outputs={"Sat": fields})["Sat"]

# run_script returns copied GetField strings; convert numerical fields explicitly.
assert all(isinstance(value, str) for value in copied.values())
final = {name: float(value) for name, value in copied.items()}
assert all(math.isfinite(value) for value in final.values())
# 1 N for 10 s, Isp = 300 s, native thruster gravity constant = 9.81 m/s^2.
expected_mass = 1010 - 10 / (300 * 9.81)
assert abs(final["TotalMass"] - expected_mass) < 2e-7

initial = (7000.0, 0.0, 0.0, 0.0, 7.546053287267836, 0.0)
coast = gmat.propagate(
    initial, "2020-07-20T12:00:00Z", [10], max_step_s=1,
    forces=gmat.ForceModel(degree=0, sun=False, moon=False, srp=False),
)[0]
expected_dv = 300 * 9.81 * math.log(1010 / expected_mass) / 1000
assert abs(final["VY"] - coast.velocity_km_s[1] - expected_dv) < 1e-7
assert final["Y"] > coast.position_km[1]
print(f"Final mass = {final['TotalMass']:.9f} kg")
print(f"Along-thrust velocity change ≈ {expected_dv * 1000:.6f} m/s")
