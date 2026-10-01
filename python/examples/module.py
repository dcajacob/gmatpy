"""Standalone value helpers and the bundled GMAT native API."""
from datetime import datetime, timezone
import gmatpy as gmat


def main():
    epoch = datetime(2020, 7, 20, 12, tzinfo=timezone.utc)
    initial = (7000, 100, -200, -0.5, 7.5, 1)
    print("Keplerian:", gmat.convert_state(initial))
    print("Earth fixed:", gmat.transform_state(initial, epoch))
    print("TT MJD:", gmat.epoch_mjd(epoch, "TT"))
    print("Moon relative to Earth:", gmat.body_state("Moon", epoch))
    print("Orbit:", gmat.propagate(initial, epoch, [0, 600])[-1].state)
    with gmat.native_session() as api:
        sat = api.Construct("Spacecraft", "ExampleSat")
        sat.SetField("DryMass", 125.)
        print("Native spacecraft mass:", sat.GetField("DryMass"))


if __name__ == "__main__":
    main()
