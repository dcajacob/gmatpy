"""Convert time, orbital elements, coordinate frames, and a Moon state."""

from datetime import datetime, timezone
import math

import gmatpy as gmat

epoch = "2020-07-20T12:00:00Z"
state = (7000.0, 100.0, -200.0, -0.5, 7.5, 1.0)

# Conventional MJD uses the 1858-11-17 origin in this interface.
utc_mjd = gmat.epoch_mjd(epoch)
expected_mjd = (
    datetime(2020, 7, 20, 12, tzinfo=timezone.utc)
    - datetime(1858, 11, 17, tzinfo=timezone.utc)
).total_seconds() / 86400
assert utc_mjd == expected_mjd
tai_mjd = gmat.epoch_mjd(epoch, scale="TAI")
tt_mjd = gmat.epoch_mjd(epoch, scale="TT")
assert abs((tai_mjd - utc_mjd) * 86400 - 37.0) < 2e-6
assert abs((tt_mjd - utc_mjd) * 86400 - 69.184) < 2e-6

# Elements are [SMA_km, e, i_deg, RAAN_deg, AOP_deg, true_anomaly_deg].
elements = gmat.convert_state(state, to_type="Keplerian")
restored = gmat.convert_state(elements, from_type="Keplerian", to_type="Cartesian")
assert math.dist(restored, state) < 2e-8

# Convert all six components: EarthFixed velocity includes frame rotation.
fixed = gmat.transform_state(state, epoch, to_frame="EarthFixed")
inertial = gmat.transform_state(
    fixed, epoch, from_frame="EarthFixed", to_frame="EarthMJ2000Eq"
)
assert math.dist(inertial, state) < 1e-6
assert abs(math.hypot(*fixed[:3]) - math.hypot(*state[:3])) < 1e-6

# This is a geometric MJ2000Eq state, with no light-time correction.
moon = gmat.body_state("Moon", epoch, origin="Earth")
assert 300000 < math.hypot(*moon[:3]) < 450000
assert gmat.body_state("Earth", epoch, origin="Moon") == tuple(-v for v in moon)

print(f"UTC MJD = {utc_mjd:.6f}; TT MJD = {tt_mjd:.9f}")
print(f"Osculating SMA = {elements[0]:.6f} km")
print(f"Geometric Earth–Moon distance = {math.hypot(*moon[:3]):.1f} km")
