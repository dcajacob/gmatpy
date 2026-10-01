"""Run after installing the wheel: python python/examples/leo.py."""

from gmatpy import ForceModel, Spacecraft, propagate

samples = propagate(
    [7000, 0, 0, 0, 7.5, 1.0],
    epoch="2020-07-20T12:00:00Z",
    times=range(0, 3601, 60),
    forces=ForceModel(degree=70, drag=True),
    spacecraft=Spacecraft(mass_kg=1000, drag_area_m2=5, srp_area_m2=5),
)
for sample in samples:
    print(sample.time_s, *sample.state)
