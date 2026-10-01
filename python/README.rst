GMAT Py: standalone Python access to GMAT
========================================

``gmatpy`` bundles GMAT R2026a's native C++ engine, its existing SWIG bindings,
and scientific inputs in a Python wheel. Install a matching wheel and import
it alongside your other Python code. No separate GMAT installation, executable,
GUI, display server, runtime download or library-path setup is required.
This is an experimental, independently packaged GMAT module; the working
package name is ``gmatpy``, version 0.2.0. It is not published to PyPI.

Install a built wheel::

    python -m pip install /path/to/gmatpy-0.2.0-*.whl

Platform support
----------------

The verified wheel is CPython 3.14 on Linux x86_64 (manylinux_2_24, glibc 2.24+).
Source metadata supports Python 3.10+, but other interpreter versions have not
been built or tested yet. Wheels are specific to their Python ABI and platform.
Windows, macOS, ARM64 and free-threaded Python wheels are not supplied or claimed
as supported yet. OS compatibility is handled by building and testing matching
wheels, rather than requiring each user to build GMAT. Python build requirements
are separate from the installed wheel's runtime, which needs only the standard
library and the bundled native binaries and data.

Propagate an orbit
------------------

::

    import gmatpy as gmat

    samples = gmat.propagate(
        [7000, 0, 0, 0, 7.5, 1.0],
        epoch="2020-07-20T12:00:00Z",
        times=range(0, 3601, 60),
        forces=gmat.ForceModel(degree=70, order=70, drag=True),
        spacecraft=gmat.Spacecraft(mass_kg=1000, drag_area_m2=5, srp_area_m2=5),
    )
    print(samples[-1].time_s, samples[-1].state)

Inputs and results are Cartesian Earth-centered mean equator/equinox J2000
(``EarthMJ2000Eq``), in km and km/s. The epoch must include a timezone; output
times are nonnegative SI seconds from the epoch in nondecreasing order.
Each call starts a new orbit. Empty times return an empty list.

* Adaptive Prince-Dormand 7/8 integration (accuracy 1e-12, max step 60 s).
* EGM96 gravity through 360x360 or JGM3 through 70x70. Default EGM96 8x8;
  degree=0 selects point-mass Earth.
* Sun/Moon point-mass gravity and spherical SRP enabled by default, using DE405.
* Optional Jacchia-Roberts drag, with constant F10.7, average F10.7 and Kp
  (defaults 150, 150, 3); disabled by default.
* Constant spacecraft mass, Cd, Cr and drag/SRP areas.

State, time, frame and ephemeris utilities
-----------------------------------------

These functions call GMAT's native routines and return plain Python values::

    elements = gmat.convert_state(samples[0].state, to_type="Keplerian")
    cartesian = gmat.convert_state(elements, from_type="Keplerian", to_type="Cartesian")
    fixed = gmat.transform_state(cartesian, "2020-07-20T12:00:00Z",
                                 to_frame="EarthFixed")
    tt_mjd = gmat.epoch_mjd("2020-07-20T12:00:00Z", scale="TT")
    moon = gmat.body_state("Moon", "2020-07-20T12:00:00Z", origin="Earth")

``convert_state`` accepts Cartesian, Keplerian, ModifiedKeplerian, Equinoctial,
ModifiedEquinoctial, SphericalRADEC and SphericalAZFPA. Cartesian is km/km/s;
Keplerian is [SMA_km, eccentricity, inclination_deg, RAAN_deg, AOP_deg,
anomaly_deg]. Other formats use GMAT's native element definitions and angular
units in degrees. The default anomaly is TA (true); MA, EA and HA may be selected.
An explicit ``mu`` in km^3/s^2 supports conversion around other central bodies;
the default is GMAT's Earth value. These are osculating, not mean/TLE elements.

``epoch_mjd`` accepts a timezone-aware datetime or ISO8601 UTC timestamp and
returns conventional MJD (JD - 2400000.5) in UTC, TAI, TT, TDB, UT1 or A1.
It does not expose GMAT's different internal ModJulian origin. Python datetime
precision applies, and literal leap-second timestamps (23:59:60) are unsupported.

``transform_state`` handles EarthMJ2000Eq, EarthMJ2000Ec, EarthICRF and EarthFixed,
including the rotating-frame velocity contribution. EarthFixed uses GMAT's
FK5/IAU1980 convention; it is not advertised as ITRF or TEME.

``body_state`` returns a geometric six-state in MJ2000Eq, in km and km/s,
relative to a selected origin. Available bodies are Sun, Moon/Luna, Mercury,
Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune and Pluto. No light-time or
aberration correction is applied. All helpers preserve the caller's directory.

Advanced native bindings
------------------------

The bundled core's existing SWIG API is available through a scoped session::

    with gmat.native_session() as api:
        sat = api.Construct("Spacecraft", "Sat")
        sat.SetField("DryMass", 125.0)
        print(sat.GetField("DryMass"))

Setup, serialization and object cleanup are automatic. Native object handles
belong to the session: never retain or use them after the block. Convenience
functions and nested sessions cannot be called inside an active session; they
raise an error instead of clearing its objects or deadlocking. The full raw API
retains GMAT's ownership conventions; use its documented API patterns when
attaching owned native objects. GUI and optional-plugin APIs are unavailable.
The value-based helpers are the preferred interface for ordinary calculations.

GMAT has process-global state. Calls are serialized; for parallel jobs use
multiprocessing with ``spawn``. Calling after ``fork`` is rejected. Do not load
another GMAT installation/API in the same process. The package uses the same
working ``gmatpy`` name as GMAT's separately installed Python API; use an isolated
virtual environment when replacing that API. Startup configuration and logs are
written to a private temporary directory, never site-packages.

Scientific inputs and limits
----------------------------

The wheel includes gravity coefficients, DE405, orientation, time and atmosphere
inputs from this checkout. They are snapshots and do not refresh automatically.
DE405 covers 1941-01-06 to 2201-02-20; Earth-orientation observations end at
2026-09-14. GMAT can extrapolate orientation outside observations with reduced
fidelity. The legacy SVN updater and Xerces are excluded. A new data updater is
deferred. Numerical regressions are provided, but this is not validated as an
operational mission-analysis tool or an STK HPOP replacement. The convenience
API does not yet expose maneuvers, estimation, STM or multi-spacecraft propagation.
Other core facilities are accessible experimentally through ``native_session``.

Building and validation
-----------------------

Source builds currently support Linux. They require a C++17 compiler, CMake,
Ninja (or Make), CPython development headers and a PIC CSPICE archive.
SWIG and scikit-build-core are Python build requirements. GMAT's existing
``depends/configure.py`` can prepare CSPICE, or point ``CSPICE_DIR`` at an
existing ``include/SpiceUsr.h`` / ``lib/cspice.a`` tree::

    python -m pip install build 'scikit-build-core>=1.0' 'swig>=4.2,<5' auditwheel patchelf ninja
    CSPICE_DIR=/path/to/cspice bash python/tools/build_wheel.sh

``GMAT_PY_PYTHON`` selects the interpreter and ``GMAT_PY_WHEEL_DIR`` the repaired
wheel output directory. The helper builds and repairs the wheel. Building in an
older manylinux image is necessary for portable Linux wheels; repair cannot
lower a compiler's glibc requirements. Direct ``python -m build --wheel`` builds
need ``-Ccmake.define.CSPICE_DIR=/path/to/cspice``. Normal GMAT builds retain the
legacy updater by default. Wheels omit duplicate unversioned linker aliases.

Install the repaired wheel in a fresh environment and run::

    python -m pip install /path/to/gmatpy-0.2.0-*.whl pytest
    python -m pytest /path/to/checkout/python/tests

``python/tools/check_wheel.py`` checks runtime dependency resolution, relocatable
library paths, no duplicate aliases and no GUI/Xerces/updater implementation.
Tests cover independent analytic propagation and element calculations, native
GMAT comparison, coordinate round trips and rotating velocity, time offsets,
ephemeris origins, native session lifetime/reentry, validation and concurrency.
