"""Solve for an instantaneous tangential burn to a specified SMA."""

import math

import gmatpy as gmat

epoch = "2020-07-20T12:00:00Z"

mu = 398600.4415
radius_km = 7000.0
state = (radius_km, 0.0, 0.0, 0.0, math.sqrt(mu / radius_km), 0.0)
target_km = 7200.0
result = gmat.target_sma(state, epoch, target_km, tolerance_km=1e-5)

# Independent vis-viva check for a tangential burn at the original radius.
expected_dv = math.sqrt(mu * (2 / radius_km - 1 / target_km)) - state[4]
assert abs(result.delta_v_km_s - expected_dv) < 2e-8
assert abs(result.residual_km) <= 1e-5
specific_energy = (sum(v * v for v in result.final_state[3:]) / 2
                   - mu / math.hypot(*result.final_state[:3]))
assert abs(-mu / (2 * specific_energy) - target_km) < 1e-5
print(f"Tangential delta-v = {result.delta_v_km_s * 1000:.6f} m/s")
print(f"Post-burn SMA = {result.achieved_sma_km:.6f} km")
