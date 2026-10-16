"""Distribution checks run against an installed wheel, using synthetic weather."""

import math
from pathlib import Path

import pytest

import gmatpy
from gmatpy import ForceModel, Spacecraft, native_session, propagate


EPOCH = "2020-07-20T12:00:00Z"
INITIAL = (6778.0, 0.0, 0.0, 0.0, math.sqrt(398600.4415 / 6778.0), 0.0)
CONSTANT = "ConstantFluxAndGeoMag"
CSSI = "CSSISpaceWeatherFile"
SCHATTEN = "SchattenFile"
WEATHER_MODES = (
    (CSSI, CONSTANT, CSSI, "CSSI space weather file"),
    (CONSTANT, CSSI, CSSI, "CSSI space weather file"),
    (CONSTANT, SCHATTEN, SCHATTEN, "predicted space weather file"),
)


def _data_root():
    return Path(gmatpy.__file__).resolve().parent / "data"


def _assert_optional_weather_is_absent():
    atmosphere = _data_root() / "atmosphere/earth"
    assert not list(atmosphere.glob("SpaceWeather*.txt"))
    assert not (atmosphere / "SchattenPredict.txt").exists()
    assert not (atmosphere / "marini.dat").exists()


def _drag_propagator(gmat, historic=CONSTANT, predicted=CONSTANT, weather=None):
    """Set up the public native API, attaching the atmosphere before file paths."""
    sat = gmat.Construct("Spacecraft", "DistributionSat")
    sat.SetField("DateFormat", "UTCGregorian")
    sat.SetField("Epoch", "20 Jul 2020 12:00:00.000")
    sat.SetField("CoordinateSystem", "EarthMJ2000Eq")
    sat.SetField("DisplayStateType", "Cartesian")
    for key, value in zip(("X", "Y", "Z", "VX", "VY", "VZ"), INITIAL):
        sat.SetField(key, value)

    fm = gmat.Construct("ForceModel", "DistributionForces")
    fm.SetField("CentralBody", "Earth")
    gravity = gmat.Construct("GravityField", "DistributionEarth")
    gravity.SetField("BodyName", "Earth")
    gravity.SetField("PotentialFile", str(_data_root() / "gravity/earth/EGM96.cof"))
    gravity.SetField("Degree", 0)
    gravity.SetField("Order", 0)
    fm.AddForce(gravity)

    drag = gmat.Construct("DragForce", "DistributionDrag")
    drag.SetField("AtmosphereModel", "JacchiaRoberts")
    # The force owns this unregistered atmosphere. Attaching it must not try to
    # open default weather files before the caller has chosen a source/path.
    atmosphere = gmat.JacchiaRobertsAtmosphere("DistributionAtmosphere")
    assert drag.SetReference(atmosphere)
    atmosphere.thisown = False
    assert not Path(drag.GetField(CSSI)).is_file()
    assert not Path(drag.GetField(SCHATTEN)).is_file()
    drag.SetField("HistoricWeatherSource", historic)
    drag.SetField("PredictedWeatherSource", predicted)
    if weather is not None:
        field, path = weather
        drag.SetField(field, str(path))
    fm.AddForce(drag)

    prop = gmat.Construct("Propagator", "DistributionProp")
    prop.SetReference(gmat.Construct("PrinceDormand78", "DistributionIntegrator"))
    prop.SetReference(fm)
    prop.SetField("InitialStepSize", 1.0)
    prop.SetField("MinStep", 0.0)
    prop.SetField("Accuracy", 1e-12)
    return sat, prop


def _prepare(gmat, sat, prop):
    gmat.Initialize()
    prop.AddPropObject(sat)
    prop.PrepareInternals()
    return prop.GetPropagator()


def _synthetic_cssi(path):
    # All numbers below are invented test values, not copied weather data.
    # CSSI's flux columns start at character 92; all eight Kp/Ap bins are flat.
    def row(day):
        columns = [2020, 7, day, 0, 0] + [30] * 8 + [240] + [15] * 8 + [15]
        prefix = " ".join(str(value) for value in columns).ljust(92)
        return prefix + "180.0 0 180.0 180.0 180.0 180.0 180.0\n"

    rows = "".join(row(day) for day in range(15, 26))
    path.write_text(
        "DATATYPE CssiSpaceWeather\n"
        "# Synthetic test fixture: every numerical value is invented.\n"
        "BEGIN OBSERVED\n" + rows + "END OBSERVED\n"
        "BEGIN DAILY_PREDICTED\n" + rows + "END DAILY_PREDICTED\n"
        "BEGIN MONTHLY_PREDICTED\nEND MONTHLY_PREDICTED\n",
        encoding="ascii",
    )


def _synthetic_schatten(path):
    # Three timing cases, each with invented mean/+2sigma/-2sigma flux and Ap.
    rows = "".join(f"{month} 2020 180 200 160 15 180 200 160 15 180 200 160 15\n"
                   for month in (6, 7, 8, 9))
    path.write_text("NOMINAL TIMING\nBEGIN_DATA\n" + rows + "END_DATA\n",
                    encoding="ascii")


def test_distribution_excludes_optional_weather_datasets():
    _assert_optional_weather_is_absent()


def test_constant_flux_drag_runs_without_optional_weather():
    _assert_optional_weather_is_absent()
    sat = Spacecraft(mass_kg=100, drag_area_m2=20)
    settings = dict(degree=0, sun=False, moon=False, srp=False)
    vacuum = propagate(INITIAL, EPOCH, [600], forces=ForceModel(**settings), spacecraft=sat)[0]
    drag = propagate(INITIAL, EPOCH, [600],
                     forces=ForceModel(**settings, drag=True, f107=200, f107a=200),
                     spacecraft=sat)[0]
    assert all(math.isfinite(value) for value in drag.state)
    assert math.dist(drag.position_km, vacuum.position_km) > 1e-7


@pytest.mark.parametrize("historic,predicted,field,message", WEATHER_MODES)
def test_selected_weather_source_requires_a_caller_file(historic, predicted, field, message):
    _assert_optional_weather_is_absent()
    with native_session() as gmat:
        sat, prop = _drag_propagator(gmat, historic, predicted)
        with pytest.raises(gmat.APIException, match="Cannot open the " + message):
            _prepare(gmat, sat, prop)


@pytest.mark.parametrize("historic,predicted,field,message", WEATHER_MODES)
def test_caller_weather_file_does_not_require_the_other_dataset(
        tmp_path, historic, predicted, field, message):
    _assert_optional_weather_is_absent()
    weather = tmp_path / "synthetic-weather.txt"
    (_synthetic_cssi if field == CSSI else _synthetic_schatten)(weather)
    with native_session() as gmat:
        sat, prop = _drag_propagator(gmat, historic, predicted, weather=(field, weather))
        integrator = _prepare(gmat, sat, prop)
        # Taking a step also exercises the actual reader, beyond filename checks.
        assert integrator.Step(1.0)
        assert all(math.isfinite(value) for value in integrator.GetState())


@pytest.mark.parametrize("missing_field,message", [
    (CSSI, "CSSI space weather file"),
    (SCHATTEN, "predicted space weather file"),
])
def test_combined_weather_sources_require_each_selected_file(tmp_path, missing_field, message):
    _assert_optional_weather_is_absent()
    provided = tmp_path / "synthetic-weather.txt"
    field = SCHATTEN if missing_field == CSSI else CSSI
    (_synthetic_cssi if field == CSSI else _synthetic_schatten)(provided)
    with native_session() as gmat:
        sat, prop = _drag_propagator(gmat, CSSI, SCHATTEN, weather=(field, provided))
        with pytest.raises(gmat.APIException, match="Cannot open the " + message):
            _prepare(gmat, sat, prop)


def test_combined_weather_sources_accept_both_caller_files(tmp_path):
    _assert_optional_weather_is_absent()
    cssi, schatten = tmp_path / "synthetic-cssi.txt", tmp_path / "synthetic-schatten.txt"
    _synthetic_cssi(cssi)
    _synthetic_schatten(schatten)
    with native_session() as gmat:
        sat, prop = _drag_propagator(gmat, CSSI, SCHATTEN, weather=(CSSI, cssi))
        drag = gmat.GetObject("DistributionDrag")
        drag.SetField(SCHATTEN, str(schatten))
        integrator = _prepare(gmat, sat, prop)
        assert integrator.Step(1.0)
        assert all(math.isfinite(value) for value in integrator.GetState())


@pytest.mark.skipif(gmatpy.capabilities().profile == "minimal", reason="SPICE kernel support is excluded")
def test_regenerated_ephemeris_sources_initialize_and_switch():
    # Initialization and source switching must use the configured renamed SPK,
    # rather than the absent old DE405AllPlanets/DE421AllPlanets filenames.
    with native_session() as gmat:
        solar = gmat.GetSolarSystem()
        assert Path(gmat.FileManager.Instance().GetFullPathname(
            "PLANETARY_SPK_FILE")).name == "gmatpy_de405_all_planets.bsp"
        epoch = gmat.A1Mjd(28917.0)
        native_state = solar.GetBody("Sun").GetMJ2000State(epoch)
        native = tuple(native_state[i] for i in range(6))
        try:
            assert solar.SetSource("SPICE")
            spice_state = solar.GetBody("Sun").GetMJ2000State(gmat.A1Mjd(28918.0))
            spice = tuple(spice_state[i] for i in range(6))
            assert all(math.isfinite(value) for value in spice)
        finally:
            assert solar.SetSource("DE405")
        restored_state = solar.GetBody("Sun").GetMJ2000State(epoch)
        restored = tuple(restored_state[i] for i in range(6))
        assert restored == native
