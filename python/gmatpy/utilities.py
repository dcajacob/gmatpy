"""Value-based access to GMAT state, coordinate, time and ephemeris bindings."""

from contextlib import contextmanager
from datetime import datetime
import math
from typing import Iterable

from . import _runtime
from ._validation import epoch_as_gmat_mjd, finite, six_vector

_STATE_TYPES = frozenset(("Cartesian", "Keplerian", "ModifiedKeplerian", "Equinoctial",
                          "ModifiedEquinoctial", "SphericalRADEC", "SphericalAZFPA"))
_FRAMES = {"EarthMJ2000Eq": "MJ2000Eq", "EarthMJ2000Ec": "MJ2000Ec",
           "EarthFixed": "BodyFixed", "EarthICRF": "ICRF"}
_BODIES = frozenset(("Sun", "Mercury", "Venus", "Earth", "Luna", "Mars", "Jupiter",
                     "Saturn", "Uranus", "Neptune", "Pluto"))
_SCALES = frozenset(("UTC", "TAI", "TT", "TDB", "UT1", "A1"))


def _copy_vector(vector):
    # SWIG's Rvector6 indexing throws APIException at index 6 rather than
    # IndexError, so tuple(vector) is not a safe way to copy it.
    result = tuple(float(vector[i]) for i in range(6))
    if not all(math.isfinite(value) for value in result):
        raise RuntimeError("GMAT returned a non-finite state")
    return result


def _a1_epoch(gmat, utc_mjd):
    converter = gmat.TimeSystemConverter.Instance()
    return converter.Convert(utc_mjd, converter.UTCMJD, converter.A1MJD)


def convert_state(state: Iterable[float], from_type: str = "Cartesian",
                  to_type: str = "Keplerian", *, mu: float | None = None,
                  anomaly: str = "TA") -> tuple[float, ...]:
    """Convert six-component orbital states using GMAT's native routines.

    Cartesian units are km and km/s. Keplerian elements are
    [SMA_km, eccentricity, inclination_deg, RAAN_deg, AOP_deg, anomaly_deg].
    mu is km^3/s^2 and defaults to GMAT's Earth constant. Angular units for
    the other supported state types follow GMAT conventions (see README).
    The default anomaly is true anomaly; MA, EA and HA are also accepted.
    """
    state = six_vector(state)
    if from_type not in _STATE_TYPES or to_type not in _STATE_TYPES:
        raise ValueError("Unsupported state type; see convert_state's supported formats")
    if anomaly not in ("TA", "MA", "EA", "HA"):
        raise ValueError("anomaly must be TA, MA, EA or HA")
    if mu is not None:
        mu = finite(mu, "mu", positive=True)
    with _runtime.operation() as gmat:
        earth = gmat.Moderator.Instance().GetSolarSystemInUse().GetBody("Earth")
        if mu is None:
            mu = earth.GetGravitationalConstant()
        converted = gmat.StateConversionUtil.Convert(
            gmat.Rvector6(*state), from_type, to_type, mu,
            earth.GetFlattening(), earth.GetEquatorialRadius(), anomaly,
        )
        return _copy_vector(converted)


def epoch_mjd(epoch: datetime | str, scale: str = "UTC") -> float:
    """Convert a timezone-aware UTC epoch to conventional MJD in a time scale.

    Supported scales are UTC, TAI, TT, TDB, UT1 and GMAT's A1. The returned
    number uses JD - 2400000.5, not GMAT's internal ModJulian origin.
    Python datetime precision applies; leap-second timestamps such as
    23:59:60 cannot be represented by this interface.
    """
    utc_mjd = float(epoch_as_gmat_mjd(epoch))
    if scale not in _SCALES:
        raise ValueError("scale must be UTC, TAI, TT, TDB, UT1 or A1")
    with _runtime.operation() as gmat:
        converter = gmat.TimeSystemConverter.Instance()
        value = converter.Convert(utc_mjd, converter.UTCMJD, getattr(converter, scale + "MJD"))
        return float(value) + 29999.5


def body_state(body: str, epoch: datetime | str, *, origin: str = "Earth") -> tuple[float, ...]:
    """Geometric body state relative to origin in MJ2000Eq, in km and km/s.

    Includes Sun, Moon/Luna and the eight planets plus Pluto, using bundled
    DE405. No light-time or aberration correction is applied.
    """
    body = "Luna" if body == "Moon" else body
    origin = "Luna" if origin == "Moon" else origin
    if body not in _BODIES or origin not in _BODIES:
        raise ValueError("body and origin must be supported solar-system bodies")
    utc_mjd = float(epoch_as_gmat_mjd(epoch))
    with _runtime.operation() as gmat:
        ss = gmat.Moderator.Instance().GetSolarSystemInUse()
        time = gmat.A1Mjd(_a1_epoch(gmat, utc_mjd))
        one = _copy_vector(ss.GetBody(body).GetMJ2000State(time))
        two = _copy_vector(ss.GetBody(origin).GetMJ2000State(time))
        return tuple(a - b for a, b in zip(one, two))


def transform_state(state: Iterable[float], epoch: datetime | str, *,
                    from_frame: str = "EarthMJ2000Eq", to_frame: str = "EarthFixed") -> tuple[float, ...]:
    """Transform position and velocity between supported Earth-centered frames.

    Frames: EarthMJ2000Eq (mean equator/equinox J2000), EarthMJ2000Ec (J2000
    ecliptic), EarthFixed (GMAT FK5/IAU1980), EarthICRF. This transforms the
    full six-state, including the rotation contribution to velocity.
    EarthFixed is not advertised as an ITRF/TEME implementation.
    """
    state = six_vector(state)
    if from_frame not in _FRAMES or to_frame not in _FRAMES:
        raise ValueError("Unsupported coordinate frame")
    utc_mjd = float(epoch_as_gmat_mjd(epoch))
    with _runtime.operation(clear=True) as gmat:
        source = gmat.Construct("CoordinateSystem", "GmatPyFrom", "Earth", _FRAMES[from_frame])
        target = gmat.Construct("CoordinateSystem", "GmatPyTo", "Earth", _FRAMES[to_frame])
        gmat.Initialize()
        converter = gmat.CoordinateConverter()
        result = gmat.Rvector6()
        if not converter.Convert(gmat.A1Mjd(_a1_epoch(gmat, utc_mjd)), gmat.Rvector6(*state),
                                 source, result, target):
            raise RuntimeError("GMAT coordinate conversion failed")
        return _copy_vector(result)


@contextmanager
def native_session():
    """Access bundled GMAT's existing SWIG API with automatic setup and cleanup.

    Example: with native_session() as gmat: sat = gmat.Construct(...).
    All native object handles belong to this session; never retain or use
    them afterward. Do not call convenience functions or nest another
    session while the context is active. Calls are serialized; use spawn
    for parallel native work. Plugin/GUI APIs are not included.
    """
    with _runtime.operation(clear=True) as gmat:
        yield gmat
