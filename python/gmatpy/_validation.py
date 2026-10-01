"""Shared scalar, vector and UTC epoch validation."""

from datetime import datetime, timezone
from decimal import Decimal
import math

def finite(value, name, *, positive=False, nonnegative=False):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(value) or (positive and value <= 0) or (nonnegative and value < 0):
        raise ValueError(f"{name} is outside its valid range")
    return value


def epoch_as_gmat_mjd(epoch):
    if isinstance(epoch, str):
        try:
            epoch = datetime.fromisoformat(epoch.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("epoch must be an ISO 8601 timestamp with a timezone") from exc
    if not isinstance(epoch, datetime) or epoch.tzinfo is None or epoch.utcoffset() is None:
        raise ValueError("epoch must be a timezone-aware datetime or ISO 8601 timestamp")
    epoch = epoch.astimezone(timezone.utc)
    # GMAT's Gregorian parser accepts exactly three fractional digits. UTC
    # ModJulian avoids truncating Python's microseconds. GMAT's MJD origin is
    # JD 2430000.0 (1941-01-05 noon), rather than the conventional JD 2400000.5.
    delta = epoch - datetime(1941, 1, 5, 12, tzinfo=timezone.utc)
    return str(Decimal(delta.days) + Decimal(delta.seconds) / Decimal(86400)
               + Decimal(delta.microseconds) / Decimal(86400000000))


def six_vector(values, name="state"):
    try:
        result = tuple(finite(value, name) for value in values)
    except TypeError as exc:
        raise ValueError(f"{name} must contain six finite numbers") from exc
    if len(result) != 6:
        raise ValueError(f"{name} must contain six finite numbers")
    return result
