"""Standalone GMAT astrodynamics: a bundled native engine and Python interfaces."""

from .propagation import ForceModel, Sample, Spacecraft, propagate
from .utilities import body_state, convert_state, epoch_mjd, native_session, transform_state

__all__ = ["ForceModel", "Sample", "Spacecraft", "propagate", "body_state", "convert_state",
           "epoch_mjd", "native_session", "transform_state"]
__version__ = "0.2.1"

from .capabilities import Capabilities, UnsupportedCapabilityError, capabilities
from .mission import Impulse, TargetResult, propagate_mission, propagate_many, run_script, target_sma
__all__ += ["Capabilities", "UnsupportedCapabilityError", "capabilities", "Impulse", "TargetResult",
            "propagate_mission", "propagate_many", "run_script", "target_sma"]
