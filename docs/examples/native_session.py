"""Use scoped native objects and recover cleanly from validation errors."""

import math

import gmatpy as gmat

epoch = "2020-07-20T12:00:00Z"
with gmat.native_session() as api:
    sat = api.Construct("Spacecraft", "ExampleSat")
    sat.SetField("DryMass", 125.0)
    mass_kg = float(sat.GetField("DryMass"))  # Copy a Python value inside the session.
    assert mass_kg == 125.0
    try:
        gmat.epoch_mjd(epoch)
    except RuntimeError as error:
        assert "cannot be nested" in str(error)
    else:
        raise AssertionError("Convenience calls must reject an active native session")
    del sat  # No native object handle is retained after this context exits.

with gmat.native_session() as api:
    assert api.Moderator.Instance().GetConfiguredObject("ExampleSat") is None

try:
    with gmat.native_session() as api:
        api.Construct("GravityField", "InvalidGravity").SetField("Degree", -1)
except Exception as error:
    # Native API exceptions vary by operation; inspect rather than suppress them.
    assert "Degree" in str(error)
else:
    raise AssertionError("Negative gravity degree should be rejected")

# Cleanup runs even when the native operation raises. A fresh helper call works.
assert math.isfinite(gmat.epoch_mjd(epoch))
print(f"Copied spacecraft mass = {mass_kg:.0f} kg; engine recovered after an error")
