"""Discover the capabilities physically included in this installed wheel."""
from dataclasses import dataclass
import json
from pathlib import Path


class UnsupportedCapabilityError(RuntimeError):
    """A requested operation is outside the selected installation profile."""


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
    if profile not in {"minimal", "extended"}:
        raise RuntimeError("Invalid installed GMAT Py build profile")
    features = {"propagation", "state_conversion", "frame_conversion", "time_conversion",
                "native_de405", "native_session"}
    if profile == "extended":
        features.update({"impulsive_maneuvers", "multi_spacecraft", "targeting", "mission_scripts", "spice_kernels"})
    return Capabilities(profile, frozenset(features), (
        "estimation/ekf", "station/measurement", "tle_propagator", "external_force_callbacks",
        "optional_optimizers", "csalt", "matlab", "gmat_functions", "gui"))


def require(feature: str):
    info = capabilities()
    if not info.supports(feature):
        raise UnsupportedCapabilityError(
            f"{feature} is unavailable in the {info.profile} GMAT Py profile. "
            "Install the extended gmatpy wheel with pip --force-reinstall to replace the minimal wheel; "
            "do not install a second distribution sharing the gmatpy namespace.")
