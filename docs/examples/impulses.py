"""Compare a maneuvering spacecraft with an unburned companion."""

import math

import gmatpy as gmat

epoch = "2020-07-20T12:00:00Z"

mu = 398600.4415
state = (7000.0, 0.0, 0.0, 0.0, math.sqrt(mu / 7000), 0.0)
forces = gmat.ForceModel(degree=0, sun=False, moon=False, srp=False)
times = [0, 60, 60, 120]
# VNB's first component follows the instantaneous velocity; 0.01 km/s = 10 m/s.
burn = gmat.Impulse(time_s=60, delta_v_km_s=(0.01, 0.0, 0.0), frame="VNB")
result = gmat.propagate_many(
    {"maneuvering": state, "companion": state},
    epoch,
    times,
    forces=forces,
    impulses={"maneuvering": [burn]},
)
baseline = gmat.propagate(state, epoch, times, forces=forces)
for companion, reference in zip(result["companion"], baseline):
    assert math.dist(companion.state, reference.state) < 1e-7

before = baseline[1]
after = result["maneuvering"][1]
assert math.dist(after.position_km, before.position_km) < 1e-7
expected_velocity = tuple(v + 0.01 * v / math.hypot(*before.velocity_km_s)
                          for v in before.velocity_km_s)
assert math.dist(after.velocity_km_s, expected_velocity) < 1e-10
assert result["maneuvering"][1] == result["maneuvering"][2]

# The single-spacecraft helper uses the same maneuver semantics.
single = gmat.propagate_mission(state, epoch, times, forces=forces, impulses=[burn])
assert math.dist(single[-1].state, result["maneuvering"][-1].state) < 1e-7
separation = math.dist(result["maneuvering"][-1].position_km,
                       result["companion"][-1].position_km)
assert separation > 0.5
print(f"Post-burn samples at 60 s agree; separation at 120 s = {separation:.6f} km")
