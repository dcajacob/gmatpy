gmat-hpop: headless GMAT propagation
====================================

This experimental package embeds GMAT R2026a's C++ engine and existing SWIG
bindings in a Python wheel. No separate GMAT installation, executable, GUI,
display server, runtime download, or environment-path setup is required.
The initial supported build is Linux, with a wheel for each CPython version.
The distribution name is ``gmat-hpop``; the import is ``gmat_hpop``.

Install a built wheel::

    python -m pip install /path/to/gmat_hpop-0.1.0-*.whl

Propagate an orbit::

    from gmat_hpop import ForceModel, Spacecraft, propagate

    samples = propagate(
        [7000, 0, 0, 0, 7.5, 1.0],
        epoch="2020-07-20T12:00:00Z",
        times=range(0, 3601, 60),
        forces=ForceModel(degree=70, order=70, drag=True),
        spacecraft=Spacecraft(mass_kg=1000, drag_area_m2=5, srp_area_m2=5),
    )
    print(samples[-1].time_s, samples[-1].state)

Inputs and results are Cartesian Earth-centered mean equator/equinox J2000
(``EarthMJ2000Eq``), in km and km/s. They are not Earth-fixed, TEME, or silently
converted from another frame. The epoch must include a timezone; elapsed output
times are nonnegative SI seconds from that epoch in nondecreasing order.
Each call starts a new orbit. Empty times return an empty list.

Included physics
----------------

* Adaptive Prince-Dormand 7/8 integration (default accuracy 1e-12, max step 60 s).
* Earth spherical-harmonic gravity: EGM96 through 360x360 or JGM3 through 70x70.
  The default is EGM96 8x8; degree=0 selects point-mass Earth.
* Sun and Moon point-mass perturbations and spherical solar radiation pressure,
  enabled by default, using the bundled DE405 planetary ephemeris.
* Optional Jacchia-Roberts atmospheric drag with explicit constant F10.7,
  average F10.7 and Kp (defaults 150, 150 and 3). Drag is disabled by default.
* Constant mass, drag/SRP areas, Cd and Cr, configurable through ``Spacecraft``.

The wheel includes gravity coefficients, DE405, time/Earth-orientation data and
atmosphere inputs from this GMAT checkout. These are snapshots; they do not
automatically refresh. The included DE405 covers 1941-01-06 to 2201-02-20;
Earth-orientation observations end at 2026-09-14. GMAT can extrapolate Earth
orientation outside the observations, with reduced fidelity. This
prototype has numerical regression checks but is not validated as an STK HPOP
replacement or for operational mission analysis. No maneuvers, estimation,
coordinate-conversion interface, STM, or multiple-spacecraft API is exposed yet.

GMAT has process-global native state. Calls are serialized, and return plain
Python values rather than engine handles. For parallel jobs use multiprocessing
with ``spawn``; calling the library after ``fork`` is rejected. Do not combine
this package with another loaded copy of GMAT in the same process. Logs and
startup configuration are written to a private temporary directory, never the
package directory; the caller's current directory is preserved.

Building
--------

Source builds require a C++17 compiler, CMake, Ninja (or Make), CPython development
headers and a position-independent CSPICE archive.
SWIG and scikit-build-core are supplied by the Python build requirements.
GMAT's existing ``depends/configure.py`` can prepare CSPICE; alternatively point
``CSPICE_DIR`` at an existing ``include/SpiceUsr.h`` and ``lib/cspice.a`` tree.
Run from the repository root::

    python -m pip install build 'scikit-build-core>=1.0' 'swig>=4.2,<5' auditwheel patchelf ninja
    CSPICE_DIR=/path/to/cspice bash python/tools/build_wheel.sh

The helper builds and repairs the wheel. The legacy SVN data updater and its
Xerces XML dependency are excluded from this package; scientific data updates
are not implemented yet. Ordinary GMAT builds retain the updater by default.
Direct ``python -m build --wheel`` builds need
``-Ccmake.define.CSPICE_DIR=/path/to/cspice``.

The first wheel uses the build host's platform and system libraries. Distribute
the repaired wheel: auditwheel assigns the compatible manylinux tag and bundles
any non-platform dependencies. Building on an older manylinux image is needed
for wider Linux compatibility; repair cannot lower a compiler's glibc
requirements. The public package is not published to PyPI yet.

Install the repaired wheel in a fresh virtual environment and run::

    python -m pip install /path/to/wheelhouse/gmat_hpop-0.1.0-*.whl pytest
    python -m pytest /path/to/checkout/python/tests

``python/tools/check_wheel.py`` checks the repaired wheel's library paths and
headless payload. ``python/tests/test_propagation.py`` checks an analytic circular
orbit, perturbation effects, repeat calls, concurrent calls and GMAT's published
JGM3 propagation example. ``python/tests/test_validation.py`` checks invalid input
and native exceptions. Raw bindings are private implementation details.
