"""Discover the capabilities physically included in this installed wheel."""
from dataclasses import dataclass
import json
from pathlib import Path


class UnsupportedCapabilityError(RuntimeError):
    """A requested operation is outside the packaged headless library."""


@dataclass(frozen=True)
class Capabilities:
    profile: str
    features: frozenset[str]
    deferred_plugins: tuple[str, ...]

    def supports(self, feature: str) -> bool:
        return feature in self.features


def capabilities() -> Capabilities:
    path = Path(__file__).with_name("BUILD_PROFILE.json")
    profile = json.loads(path.read_text())["profile"] if path.exists() else "extended"
    if profile != "extended":
        raise RuntimeError("GMAT Py requires the standard full headless package; obsolete or invalid build record")
    features = {"propagation", "state_conversion", "frame_conversion", "time_conversion",
                "native_de405", "native_session", "impulsive_maneuvers",
                "multi_spacecraft", "targeting", "mission_scripts", "spice_kernels"}
    return Capabilities(profile, frozenset(features), (
        "estimation/ekf", "station/measurement", "tle_propagator", "external_force_callbacks",
        "optional_optimizers", "csalt", "matlab", "gmat_functions"))


def require(feature: str):
    info = capabilities()
    if not info.supports(feature):
        raise UnsupportedCapabilityError(
            f"{feature} is unavailable in the packaged GMAT Py headless library.")
