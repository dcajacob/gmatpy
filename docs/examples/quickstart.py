"""Propagate a circular orbit with point-mass Earth gravity."""

import math

import gmatpy as gmat

epoch = "2020-07-20T12:00:00Z"
mu = 398600.4415  # Earth's GMAT gravitational parameter, km^3/s^2.
radius_km = 7000.0
state = (radius_km, 0.0, 0.0, 0.0, math.sqrt(mu / radius_km), 0.0)
forces = gmat.ForceModel(degree=0, sun=False, moon=False, srp=False)

# These are elapsed seconds from epoch, not incremental step lengths.
samples = gmat.propagate(state, epoch, [0, 300, 600], forces=forces)

assert [sample.time_s for sample in samples] == [0, 300, 600]
assert math.dist(samples[0].state, state) < 1e-9
angle = math.sqrt(mu / radius_km**3) * 600
expected_position = (radius_km * math.cos(angle), radius_km * math.sin(angle), 0.0)
assert math.dist(samples[-1].position_km, expected_position) < 1e-5
assert abs(math.hypot(*samples[-1].position_km) - radius_km) < 1e-5

last = samples[-1]
print(f"t = {last.time_s:.0f} s; radius = {math.hypot(*last.position_km):.6f} km")
print("position (km):", tuple(round(value, 6) for value in last.position_km))
