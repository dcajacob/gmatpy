from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Inexact, localcontext
import math
import pytest

from gmatpy import (body_state, convert_state, epoch_mjd, native_session,
                    propagate, transform_state)

EPOCH = "2020-07-20T12:00:00Z"
STATE = (7000., 100., -200., -0.5, 7.5, 1.)


@pytest.mark.parametrize("kind", ["Keplerian", "ModifiedKeplerian", "Equinoctial",
                                  "ModifiedEquinoctial", "SphericalRADEC", "SphericalAZFPA"])
def test_state_conversions_round_trip(kind):
    converted = convert_state(STATE, to_type=kind)
    assert isinstance(converted, tuple) and len(converted) == 6
    restored = convert_state(converted, from_type=kind, to_type="Cartesian")
    assert restored == pytest.approx(STATE, rel=0, abs=2e-9)


@pytest.mark.parametrize(("to_type", "expected"), [
    ("Keplerian", (10000, 0.2, 30, 40, 50, 60)),
    ("ModifiedKeplerian", (8000, 12000, 30, 40, 50, 60)),
])
def test_equinoctial_direct_to_keplerian(to_type, expected):
    cart = convert_state((10000, 0.2, 30, 40, 50, 60), "Keplerian", "Cartesian")
    equinoctial = convert_state(cart, "Cartesian", "Equinoctial")
    actual = convert_state(equinoctial, "Equinoctial", to_type)
    assert actual == pytest.approx(expected, rel=0, abs=2e-9)


@pytest.mark.parametrize("angle_deg", [-60, 60])
@pytest.mark.parametrize(("anomaly", "sma", "ecc"), [("EA", 10000, 0.2), ("HA", -10000, 1.5)])
def test_keplerian_anomaly_against_planar_conic(anomaly, sma, ecc, angle_deg):
    mu = 398600.4415
    angle = math.radians(angle_deg)
    # Perifocal x and y, differentiated using Kepler's equation for velocity.
    if anomaly == "EA":
        c, s = math.cos(angle), math.sin(angle)
        y_scale = math.sqrt(1 - ecc**2)
        rate = math.sqrt(mu / sma**3) / (1 - ecc * c)
        x, y = sma * (c - ecc), sma * y_scale * s
        vx, vy = -sma * s * rate, sma * y_scale * c * rate
    else:
        c, s = math.cosh(angle), math.sinh(angle)
        y_scale = math.sqrt(ecc**2 - 1)
        rate = math.sqrt(mu / abs(sma)**3) / (ecc * c - 1)
        x, y = sma * (c - ecc), -sma * y_scale * s
        vx, vy = sma * s * rate, -sma * y_scale * c * rate
    actual = convert_state((sma, ecc, 0, 0, 0, angle_deg), "Keplerian", "Cartesian",
                           mu=mu, anomaly=anomaly)
    assert actual[:3] == pytest.approx((x, y, 0), rel=0, abs=2e-9)
    assert actual[3:] == pytest.approx((vx, vy, 0), rel=0, abs=2e-12)


@pytest.mark.parametrize("anomaly", ["TA", "MA", "EA"])
def test_keplerian_conversion_against_analytic_periapsis(anomaly):
    mu = 398600.4415
    a, e = 10000., 0.2
    radius = a * (1-e)
    speed = math.sqrt(mu * (1+e) / (a * (1-e)))
    expected = (radius, 0, 0, 0, speed, 0)
    converted = convert_state([a,e,0,0,0,0], from_type="Keplerian", to_type="Cartesian",
                              mu=mu, anomaly=anomaly)
    assert converted == pytest.approx(expected, rel=0, abs=1e-9)


def test_custom_gravitational_parameter():
    mu = 42828.375214
    sample = convert_state([4000,0,0,0,math.sqrt(mu/4000),0], mu=mu)
    assert sample[:3] == pytest.approx((4000,0,0), abs=1e-9)


def test_time_scale_offsets_and_conventional_mjd():
    # Independent Gregorian-to-MJD calculation; July 2020 TAI-UTC is 37 s.
    epoch = datetime(2020,7,20,12,tzinfo=timezone.utc)
    expected = (epoch-datetime(1858,11,17,tzinfo=timezone.utc)).total_seconds()/86400
    utc = epoch_mjd(EPOCH)
    assert utc == expected
    assert epoch_mjd("2020-07-20T06:00:00-06:00") == utc
    assert (epoch_mjd(EPOCH,"TAI")-utc)*86400 == pytest.approx(37,abs=2e-6)
    assert (epoch_mjd(EPOCH,"TT")-utc)*86400 == pytest.approx(69.184,abs=2e-6)
    assert abs(epoch_mjd(EPOCH,"TDB")-epoch_mjd(EPOCH,"TT"))*86400 < 0.003
    assert abs(epoch_mjd(EPOCH,"UT1")-utc)*86400 < 1
    assert abs(epoch_mjd(EPOCH,"A1")-epoch_mjd(EPOCH,"TAI"))*86400 < 0.04


@pytest.mark.parametrize("trap_inexact", [False, True])
def test_epoch_preserves_microseconds_under_caller_decimal_context(trap_inexact):
    timestamp = "2020-07-20T12:34:56.123456Z"
    expected = 59050 + (12 * 3600 + 34 * 60 + 56.123456) / 86400
    with localcontext() as context:
        context.prec = 8
        context.traps[Inexact] = trap_inexact
        context.clear_flags()
        assert epoch_mjd(timestamp) == pytest.approx(expected, rel=0, abs=math.ulp(expected))
        assert not context.flags[Inexact]


@pytest.mark.parametrize("frame", ["EarthFixed", "EarthMJ2000Ec", "EarthICRF"])
def test_frame_conversion_round_trip_and_norm(frame):
    converted = transform_state(STATE,EPOCH,to_frame=frame)
    assert math.hypot(*converted[:3]) == pytest.approx(math.hypot(*STATE[:3]),abs=2e-8)
    restored = transform_state(converted,EPOCH,from_frame=frame,to_frame="EarthMJ2000Eq")
    assert restored == pytest.approx(STATE,rel=0,abs=2e-8)


def test_earth_fixed_velocity_includes_rotation():
    stationary = transform_state([7000,0,0,0,0,0],EPOCH)
    assert 0.50 < math.hypot(*stationary[3:]) < 0.52
    assert transform_state(STATE,EPOCH,from_frame="EarthMJ2000Eq",
                           to_frame="EarthMJ2000Eq") == STATE


def test_geometric_ephemeris_and_origin_composition():
    moon = body_state("Moon",EPOCH)
    assert 300000 < math.hypot(*moon[:3]) < 450000
    assert moon == body_state("Luna",EPOCH)
    assert body_state("Earth",EPOCH,origin="Earth") == (0,)*6
    assert body_state("Earth",EPOCH,origin="Moon") == tuple(-v for v in moon)
    sun_earth = body_state("Sun",EPOCH)
    sun_moon = body_state("Sun",EPOCH,origin="Moon")
    assert sun_moon == pytest.approx(tuple(s-m for s,m in zip(sun_earth,moon)),abs=1e-9)
    assert 1.4e8 < math.hypot(*sun_earth[:3]) < 1.6e8


@pytest.mark.parametrize("body", ["Mercury","Venus","Mars","Jupiter","Saturn",
                                   "Uranus","Neptune","Pluto"])
def test_other_planets_return_finite_states(body):
    assert all(math.isfinite(v) for v in body_state(body,EPOCH))


def test_native_session_scope_cleanup_and_reentry_rejection():
    with native_session() as gmat:
        sat = gmat.Construct("Spacecraft","AdvancedSat")
        sat.SetField("DryMass",125.)
        assert sat.GetField("DryMass") == "125"
        assert hasattr(gmat,"CoordinateConverter")
        with pytest.raises(RuntimeError,match="cannot be nested"):
            epoch_mjd(EPOCH)
        with pytest.raises(RuntimeError,match="cannot be nested"):
            with native_session():
                pass
        with pytest.raises(RuntimeError,match="cannot be nested"):
            propagate(STATE,EPOCH,[60])
    # Never touch sat after the session; native handles have been cleared.
    with native_session() as gmat:
        assert gmat.Moderator.Instance().GetConfiguredObject("AdvancedSat") is None
    assert len(propagate(STATE,EPOCH,[60])) == 1


def test_native_exception_leaves_session_and_engine_usable():
    with pytest.raises(Exception,match="Degree"):
        with native_session() as gmat:
            gmat.Construct("GravityField","BadGravity").SetField("Degree",-1)
    assert math.isfinite(epoch_mjd(EPOCH))


def test_mixed_threads_do_not_clear_another_operation():
    def task(i):
        if i%2:
            return body_state("Moon",EPOCH)
        return transform_state(STATE,EPOCH)
    expected = [task(i) for i in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(task,range(4))) == expected


@pytest.mark.parametrize("call", [
    lambda: convert_state([1,2]), lambda: convert_state(STATE,to_type="invalid"),
    lambda: convert_state(STATE,mu=-1), lambda: convert_state(STATE,anomaly="invalid"),
    lambda: epoch_mjd(EPOCH,"invalid"), lambda: epoch_mjd("2020-01-01"),
    lambda: body_state("invalid",EPOCH), lambda: body_state("Moon",EPOCH,origin="invalid"),
    lambda: transform_state(STATE,EPOCH,to_frame="TEME"),
    lambda: transform_state([float('nan')]*6,EPOCH),
])
def test_invalid_utility_inputs(call):
    with pytest.raises(ValueError):
        call()
