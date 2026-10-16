"""Value-based core mission workflows for the extended build profile.

Impulses do not consume mass. Outputs at an impulse epoch are post-burn;
coincident burns execute in input order. No optional plugins are required.
"""
from dataclasses import dataclass
import math
from pathlib import Path
import tempfile
from collections.abc import Mapping

from . import _runtime
from ._validation import finite, six_vector, epoch_as_gmat_mjd
from .capabilities import require
from .propagation import ForceModel, Spacecraft, Sample, _make_setup


@dataclass(frozen=True)
class Impulse:
    time_s: float
    delta_v_km_s: tuple[float, float, float]
    frame: str = "EarthMJ2000Eq"

    def __post_init__(self):
        object.__setattr__(self, "time_s", finite(self.time_s, "burn time", nonnegative=True))
        vector = tuple(finite(v, "delta-v") for v in self.delta_v_km_s)
        if len(vector) != 3:
            raise ValueError("delta_v_km_s must contain three finite components")
        object.__setattr__(self, "delta_v_km_s", vector)
        if self.frame not in {"EarthMJ2000Eq", "VNB"}:
            raise ValueError("Impulse frame must be EarthMJ2000Eq or VNB")


def propagate_many(states: Mapping[str, object], epoch, times, *, forces=None,
                   spacecraft=None, impulses=None, accuracy=1e-12, max_step_s=60.0):
    """Co-propagate named EarthMJ2000Eq states in one native propagator.

    The force settings are common; spacecraft properties and impulse schedules
    are mappings keyed by state name. Returns name -> list[Sample]. This is not
    the optional GMAT Formation plugin. All results are copied Python values.
    """
    require("multi_spacecraft")
    if not isinstance(states, Mapping) or not states:
        raise ValueError("states must be a nonempty mapping of names to six-states")
    if any(not isinstance(name, str) or not name for name in states):
        raise ValueError("spacecraft names must be nonempty strings")
    states = {name: six_vector(state) for name, state in states.items()}
    if any(math.hypot(*state[:3]) == 0 for state in states.values()):
        raise ValueError("spacecraft positions must be nonzero")
    epoch = epoch_as_gmat_mjd(epoch)
    times = tuple(finite(t, "times", nonnegative=True) for t in times)
    if any(a > b for a, b in zip(times, times[1:])):
        raise ValueError("times must be nondecreasing")
    accuracy = finite(accuracy, "accuracy", positive=True)
    max_step_s = finite(max_step_s, "max_step_s", positive=True)
    forces = ForceModel() if forces is None else forces
    if not isinstance(forces, ForceModel):
        raise TypeError("forces must be ForceModel")
    properties = {} if spacecraft is None else dict(spacecraft)
    schedules = {} if impulses is None else dict(impulses)
    if (properties.keys() | schedules.keys()) - states.keys():
        raise ValueError("spacecraft and impulse names must exist in states")
    properties = {name: properties.get(name, Spacecraft()) for name in states}
    if any(not isinstance(value, Spacecraft) for value in properties.values()):
        raise TypeError("spacecraft properties must be Spacecraft values")
    events = []
    for name, burns in schedules.items():
        for burn in burns:
            if not isinstance(burn, Impulse):
                raise TypeError("impulses must contain Impulse values")
            if not times or burn.time_s > times[-1]:
                raise ValueError("impulse lies beyond the sampled mission interval")
            events.append((burn.time_s, name, burn))
    events.sort(key=lambda event: event[0])
    results = {name: [] for name in states}
    if not times:
        return results
    with _runtime.operation(clear=True) as gmat:
        prop, integrator, satellites = _make_setup(
            gmat, states, epoch, forces, properties, accuracy, max_step_s)
        burns = []
        for index, (_, name, event) in enumerate(events):
            burn = gmat.Construct("ImpulsiveBurn", f"GmatPyBurn{index}")
            burn.SetField("CoordinateSystem", "Local")
            burn.SetField("Origin", "Earth")
            burn.SetField("Axes", "MJ2000Eq" if event.frame == "EarthMJ2000Eq" else "VNB")
            burn.SetField("DecrementMass", False)
            for field, value in zip(("Element1", "Element2", "Element3"), event.delta_v_km_s):
                burn.SetField(field, value)
            burn.SetSolarSystem(gmat.GetSolarSystem())
            burn.SetSpacecraftToManeuver(satellites[name])
            burns.append(burn)
        elapsed, event_index = 0.0, 0
        for target in times:
            while elapsed < target or (event_index < len(events) and events[event_index][0] <= target):
                next_time = min(target, events[event_index][0] if event_index < len(events) else target)
                while elapsed < next_time:
                    step = min(max_step_s, next_time - elapsed)
                    if elapsed + step == elapsed:
                        raise RuntimeError("Mission time exceeds floating-point time resolution")
                    if not integrator.Step(step):
                        raise RuntimeError(f"GMAT propagation failed at {elapsed} seconds")
                    elapsed += step
                if event_index < len(events) and events[event_index][0] == elapsed:
                    integrator.UpdateSpaceObject()
                    if not burns[event_index].Fire():
                        raise RuntimeError("Native impulsive maneuver failed")
                    integrator.UpdateFromSpaceObject()
                    event_index += 1
            state = tuple(integrator.GetState())
            if len(state) != 6 * len(states) or not all(math.isfinite(v) for v in state):
                raise RuntimeError("GMAT returned an invalid multi-spacecraft state")
            for index, name in enumerate(states):
                current = state[6*index:6*index+6]
                results[name].append(Sample(target, current[:3], current[3:]))
    return results


def propagate_mission(state, epoch, times, *, impulses=(), forces=None,
                      spacecraft=None, accuracy=1e-12, max_step_s=60.0):
    """Sample one spacecraft with scheduled native impulsive maneuvers."""
    require("impulsive_maneuvers")
    return propagate_many({"sat": state}, epoch, times, forces=forces,
                          spacecraft={"sat": Spacecraft() if spacecraft is None else spacecraft},
                          impulses={"sat": impulses}, accuracy=accuracy, max_step_s=max_step_s)["sat"]


def run_script(path, *, outputs):
    """Execute a trusted core GMAT script and copy requested runtime fields.

    outputs maps object names to field names; returns nested dictionaries of
    native GetField strings. Scripts can write files and run command loops;
    this is not a sandbox or a promise of arbitrary GMAT/plugin compatibility.
    All native objects are cleared even if loading/execution/field access fails.
    """
    require("mission_scripts")
    path = Path(path).expanduser().resolve(strict=True)
    if not isinstance(outputs, Mapping):
        raise TypeError("outputs must map object names to field name sequences")
    if any(isinstance(fields, str) for fields in outputs.values()):
        raise TypeError("output fields must be sequences, not a string")
    outputs = {name: tuple(fields) for name, fields in outputs.items()}
    if any(not isinstance(name, str) or not name for name in outputs):
        raise ValueError("output object names must be nonempty strings")
    if any(not isinstance(field, str) or not field for fields in outputs.values() for field in fields):
        raise ValueError("output field names must be nonempty strings")
    with _runtime.operation(clear=True) as gmat:
        if not gmat.LoadScript(str(path)):
            raise RuntimeError(f"GMAT could not load script: {path}")
        if not gmat.RunScript():
            raise RuntimeError(f"GMAT mission did not complete successfully: {path}")
        result = {}
        for name, fields in outputs.items():
            try:
                obj = gmat.GetRuntimeObject(name)
            except gmat.APIException as error:
                raise ValueError(f"Runtime object not found: {name}") from error
            if obj is None:
                raise ValueError(f"Runtime object not found: {name}")
            result[name] = {field: obj.GetField(field) for field in fields}
        return result


@dataclass(frozen=True)
class TargetResult:
    delta_v_km_s: float
    final_state: tuple[float, ...]
    achieved_sma_km: float
    residual_km: float


def target_sma(state, epoch, target_sma_km, *, tolerance_km=1e-5, max_iterations=25):
    """Target an instantaneous tangential VNB burn using GMAT DifferentialCorrector.

    Earth-centered elliptic starting orbits only. This solves post-burn SMA at
    the input epoch; it is not a transfer/time-of-flight or fuel-mass optimizer.
    Raises if the bounded native solve does not meet the requested residual.
    """
    require("targeting")
    state = six_vector(state)
    epoch = epoch_as_gmat_mjd(epoch)
    target_sma_km = finite(target_sma_km, "target_sma_km", positive=True)
    tolerance_km = finite(tolerance_km, "tolerance_km", positive=True)
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or not 1 <= max_iterations <= 100:
        raise ValueError("max_iterations must be an integer from 1 through 100")
    from .utilities import convert_state
    initial = convert_state(state)
    if initial[0] <= 0 or not 0 <= initial[1] < 1:
        raise ValueError("target_sma requires an elliptic initial state")
    fields = ("X", "Y", "Z", "VX", "VY", "VZ")
    lines = ["Create Spacecraft Sat;", "Sat.DateFormat = UTCModJulian;",
             f"Sat.Epoch = '{epoch}';", "Sat.CoordinateSystem = EarthMJ2000Eq;",
             "Sat.DisplayStateType = Cartesian;"]
    lines += [f"Sat.{field} = {value:.17g};" for field, value in zip(fields, state)]
    lines += ["Create ImpulsiveBurn Burn;", "Burn.CoordinateSystem = Local;",
              "Burn.Origin = Earth;", "Burn.Axes = VNB;", "Burn.DecrementMass = false;",
              "Burn.Element2 = 0;", "Burn.Element3 = 0;", "Create DifferentialCorrector DC;",
              f"DC.MaximumIterations = {max_iterations};", "BeginMissionSequence;",
              "Target DC {SolveMode = Solve, ExitMode = SaveAndContinue, ShowProgressWindow = false};",
              "Vary DC(Burn.Element1 = 0, {Perturbation = 0.00001, Lower = -10, Upper = 10, MaxStep = 0.5});",
              "Maneuver Burn(Sat);",
              f"Achieve DC(Sat.Earth.SMA = {target_sma_km:.17g}, {{Tolerance = {tolerance_km:.17g}}});",
              "EndTarget;"]
    with tempfile.TemporaryDirectory(prefix="gmatpy-target-") as directory:
        script = Path(directory) / "target.script"
        script.write_text("\n".join(lines)+"\n")
        result = run_script(script, outputs={"Sat": fields, "Burn": ("Element1",)})
    final = tuple(float(result["Sat"][field]) for field in fields)
    achieved = convert_state(final)[0]
    residual = achieved-target_sma_km
    if abs(residual) > tolerance_km:
        raise RuntimeError(f"GMAT target did not converge: SMA residual {residual} km")
    return TargetResult(float(result["Burn"]["Element1"]), final, achieved, residual)
