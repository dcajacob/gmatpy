"""A small value-based facade over GMAT's propagation setup API."""

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Iterable

from . import _runtime
from ._validation import finite as _finite, epoch_as_gmat_mjd as _epoch_string, six_vector


@dataclass(frozen=True)
class Spacecraft:
    """Constant spacecraft properties used by spherical drag and SRP models."""

    mass_kg: float = 1000.0
    drag_area_m2: float = 1.0
    srp_area_m2: float = 1.0
    cd: float = 2.2
    cr: float = 1.8

    def __post_init__(self):
        for name in ("mass_kg", "cd", "cr"):
            object.__setattr__(self, name, _finite(getattr(self, name), name, positive=True))
        for name in ("drag_area_m2", "srp_area_m2"):
            object.__setattr__(self, name, _finite(getattr(self, name), name, nonnegative=True))


@dataclass(frozen=True)
class ForceModel:
    """Earth gravity plus optional perturbations; degree=0 means point-mass Earth.

    Drag uses Jacchia-Roberts with explicit constant F10.7, average F10.7 and Kp.
    EGM96 supports degree/order through 360; JGM3 supports through 70.
    """

    gravity_model: str = "EGM96"
    degree: int = 8
    order: int | None = None
    sun: bool = True
    moon: bool = True
    srp: bool = True
    drag: bool = False
    f107: float = 150.0
    f107a: float = 150.0
    kp: float = 3.0

    def __post_init__(self):
        if self.gravity_model not in ("EGM96", "JGM3"):
            raise ValueError("gravity_model must be EGM96 or JGM3")
        limit = 360 if self.gravity_model == "EGM96" else 70
        order = self.degree if self.order is None else self.order
        for name, value in (("degree", self.degree), ("order", order)):
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= limit:
                raise ValueError(f"{name} must be an integer between 0 and {limit}")
        if order > self.degree:
            raise ValueError("order cannot exceed degree")
        object.__setattr__(self, "order", order)
        for name in ("sun", "moon", "srp", "drag"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be a bool")
        for name in ("f107", "f107a"):
            object.__setattr__(self, name, _finite(getattr(self, name), name, positive=True))
        kp = _finite(self.kp, "kp", nonnegative=True)
        if kp > 9:
            raise ValueError("kp must be between 0 and 9")
        object.__setattr__(self, "kp", kp)


@dataclass(frozen=True)
class Sample:
    """State at elapsed SI seconds from the input UTC epoch, in EarthMJ2000Eq.

    EarthMJ2000Eq is GMAT's Earth-centered mean equator/equinox J2000 frame.
    Position is km; velocity is km/s. It is not an Earth-fixed or TEME frame.
    """

    time_s: float
    position_km: tuple[float, float, float]
    velocity_km_s: tuple[float, float, float]

    @property
    def state(self):
        return self.position_km + self.velocity_km_s


def propagate(
    state: Iterable[float],
    epoch: datetime | str,
    times: Iterable[float],
    *,
    forces: ForceModel | None = None,
    spacecraft: Spacecraft | None = None,
    accuracy: float = 1e-12,
    max_step_s: float = 60.0,
) -> list[Sample]:
    """Propagate an EarthMJ2000Eq Cartesian state to nondecreasing output times.

    ``state`` is [x, y, z, vx, vy, vz] in km and km/s. ``times`` contains
    nonnegative elapsed seconds from ``epoch``, not incremental step sizes.
    Every call starts a fresh orbit. Calls are serialized because the GMAT
    engine has process-global state; use spawned processes for parallel jobs.
    """
    _runtime.check_process()
    state = six_vector(state)
    if len(state) != 6 or math.hypot(*state[:3]) == 0:
        raise ValueError("state must have six components and a nonzero position")
    epoch = _epoch_string(epoch)
    times = tuple(_finite(value, "times", nonnegative=True) for value in times)
    if any(b < a for a, b in zip(times, times[1:])):
        raise ValueError("times must be nondecreasing elapsed seconds")
    forces = ForceModel() if forces is None else forces
    spacecraft = Spacecraft() if spacecraft is None else spacecraft
    if not isinstance(forces, ForceModel) or not isinstance(spacecraft, Spacecraft):
        raise TypeError("forces and spacecraft must be ForceModel and Spacecraft instances")
    accuracy = _finite(accuracy, "accuracy", positive=True)
    max_step_s = _finite(max_step_s, "max_step_s", positive=True)
    if not times:
        return []
    with _runtime.operation(clear=True) as gmat:
        return _propagate(gmat, state, epoch, times, forces, spacecraft, accuracy, max_step_s)


def _propagate(gmat, state, epoch, times, forces, spacecraft, accuracy, max_step_s):
    from pathlib import Path

    sat = gmat.Construct("Spacecraft", "GmatPySat")
    sat.SetField("DateFormat", "UTCModJulian")
    sat.SetField("Epoch", epoch)
    sat.SetField("CoordinateSystem", "EarthMJ2000Eq")
    sat.SetField("DisplayStateType", "Cartesian")
    for key, value in zip(("X", "Y", "Z", "VX", "VY", "VZ"), state):
        sat.SetField(key, value)
    for key, value in (("DryMass", spacecraft.mass_kg), ("Cd", spacecraft.cd),
                       ("Cr", spacecraft.cr), ("DragArea", spacecraft.drag_area_m2),
                       ("SRPArea", spacecraft.srp_area_m2)):
        sat.SetField(key, value)
    fm = gmat.Construct("ForceModel", "GmatPyForces")
    fm.SetField("CentralBody", "Earth")
    if forces.degree == 0 and not forces.drag:
        gravity = gmat.Construct("PointMassForce", "GmatPyEarth")
    else:
        # GMAT requires a primary GravityField body for drag. A degree/order
        # zero field supplies the same monopole when only drag is requested.
        gravity = gmat.Construct("GravityField", "GmatPyEarth")
        gravity.SetField("PotentialFile", str(Path(__file__).resolve().parent /
                         "data/gravity/earth" / f"{forces.gravity_model}.cof"))
        gravity.SetField("Degree", forces.degree)
        gravity.SetField("Order", forces.order)
    gravity.SetField("BodyName", "Earth")
    fm.AddForce(gravity)
    for enabled, body in ((forces.sun, "Sun"), (forces.moon, "Luna")):
        if enabled:
            point_mass = gmat.Construct("PointMassForce", f"GmatPy{body}")
            point_mass.SetField("BodyName", body)
            fm.AddForce(point_mass)
    if forces.srp:
        fm.AddForce(gmat.Construct("SolarRadiationPressure", "GmatPySrp"))
    if forces.drag:
        drag = gmat.Construct("DragForce", "GmatPyDrag")
        drag.SetField("AtmosphereModel", "JacchiaRoberts")
        # DragForce takes ownership of its atmosphere. Construct() would also
        # register it with ConfigManager, causing both owners to delete it on
        # Clear(). Create an unregistered atmosphere and transfer ownership.
        atmosphere = gmat.JacchiaRobertsAtmosphere("GmatPyAtmosphere")
        if not drag.SetReference(atmosphere):
            raise RuntimeError("GMAT could not attach the Jacchia-Roberts atmosphere")
        atmosphere.thisown = False
        drag.SetField("HistoricWeatherSource", "ConstantFluxAndGeoMag")
        drag.SetField("PredictedWeatherSource", "ConstantFluxAndGeoMag")
        drag.SetField("F107", forces.f107)
        drag.SetField("F107A", forces.f107a)
        drag.SetField("MagneticIndex", forces.kp)
        fm.AddForce(drag)
    prop = gmat.Construct("Propagator", "GmatPyProp")
    prop.SetReference(gmat.Construct("PrinceDormand78", "GmatPyIntegrator"))
    prop.SetReference(fm)
    prop.SetField("InitialStepSize", max_step_s)
    prop.SetField("MaxStep", max_step_s)
    prop.SetField("MinStep", 0.0)
    prop.SetField("Accuracy", accuracy)
    gmat.Initialize()
    prop.AddPropObject(sat)
    prop.PrepareInternals()
    integrator = prop.GetPropagator()
    samples = []
    elapsed = 0.0
    for target in times:
        # Bound each API call too: Step(dt) otherwise has a fixed attempt limit
        # for long output intervals even though the internal integration adapts.
        while elapsed < target:
            delta = min(max_step_s, target - elapsed)
            if elapsed + delta == elapsed:
                raise RuntimeError("Output time exceeds floating-point time resolution")
            if not integrator.Step(delta):
                raise RuntimeError(f"GMAT propagation failed at {elapsed} seconds")
            elapsed += delta
        current = tuple(integrator.GetState())
        if len(current) != 6 or not all(math.isfinite(value) for value in current):
            raise RuntimeError("GMAT returned an invalid Cartesian state")
        samples.append(Sample(target, current[:3], current[3:]))
    return samples
