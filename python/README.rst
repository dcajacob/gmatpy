GMAT Py: standalone Python access to GMAT
===========================================

``gmatpy`` bundles GMAT R2026a's native C++ engine, its existing SWIG bindings,
and scientific inputs in a Python wheel. Install a matching wheel and import
it alongside your other Python code. No separate GMAT installation, executable,
GUI, display server, runtime download or library-path setup is required.
This is an experimental, independently packaged GMAT module; the working
package name is ``gmatpy``, version 0.2.0. It is not published to PyPI.

Install a built wheel::

    python -m pip install /path/to/gmatpy-0.2.0-*.whl

Platform support
------------------

This package ships one complete headless library with SPICE and all seventeen
curated scientific inputs. There is no profile selection or feature extra.
The historical ``extended`` value returned by ``capabilities().profile`` is an
internal compatibility label. No GUI is included or planned for GMAT Py.

The most recent native qualification is for source
``bff0ed4687964cd1f36a3ebaeb278b451bac271d``, before this packaging cleanup.
Its full headless wheels passed 144 tests with two expected skips on Linux
x86_64 and ARM64 and macOS Intel/ARM64 on the first attempt, using standard-ABI
CPython 3.14.7 (Linux ARM64: 3.14.8). The cleanup retains the full
native configuration and scientific inputs; tests reusing earlier extended
binaries do not make them newly built artifacts of this source revision.
Final release files require their own source/build receipts and validation.

The earlier minimal/extended wheel variants and Windows results are historical.
Python 3.10+ metadata is broader than the qualified interpreter scope; other
Python versions and free-threaded Python remain unqualified. Wheels are specific
to their Python ABI and platform. Runtime needs only the standard library and
bundled native binaries/data; source-build requirements are separate.
This qualification does not imply public binary availability.

Documentation
---------------

Read the `hosted documentation <https://gmatpy.readthedocs.io/en/latest/>`_ for
installation, quickstart, TLE Tailor integration, time/frames/units, public Python
exports, scripts, native access, examples and development. The Sphinx sources
are in ``docs/``. To render locally, install ``docs/requirements.txt`` and run
``python -m sphinx -W --keep-going -n -b html docs docs/_build/html`` from the
repository root. This does not install or compile GMAT.

Propagate an orbit
--------------------

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
--------------------------------------------

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
The native MJ2000Eq/ICRF link applies the same table-derived rotation to position
and velocity and uses a zero rotation derivative; it does not differentiate
the ICRF table with respect to time.

``body_state`` returns a geometric six-state in MJ2000Eq, in km and km/s,
relative to a selected origin. Available bodies are Sun, Moon/Luna, Mercury,
Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune and Pluto. No light-time or
aberration correction is applied. All helpers preserve the caller's directory.

Advanced native bindings
--------------------------

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
------------------------------

The wheel includes gravity coefficients, DE405, orientation, time and the
exponential-atmosphere table from this checkout. They are snapshots and do not
refresh automatically. AGI/CSSI space-weather files, Schatten forecasts and the
unused ``marini.dat`` table are deliberately excluded from wheels and source
archives while their redistribution terms/provenance remain unresolved. The
``propagate`` helper uses constant F10.7/F10.7A/Kp values and does not need these
files. Advanced file-based weather models require caller-supplied licensed
inputs via ``CSSISpaceWeatherFile``/``SchattenFile``; absent selected inputs raise
an exception, with no automatic download or substitute predictions.
Native DE405 covers 1941-01-06 to 2201-02-20; the inherited Earth-orientation
snapshot ends at 2026-09-14 and includes predicted rows. GMAT can extrapolate
orientation outside the snapshot with reduced fidelity. The restored NASA
``ICRF_Table.txt`` retains its irregular grid and internal gaps, with table
coverage approximately 1960-01-01 through 2100-01-01. The restored March 2026
Earth high-precision PCK ends on 2026-06-12; that SPICE-frame limit is separate
from the default FK5/EOP path. The legacy SVN updater and Xerces are excluded. A new data updater is
deferred. Numerical regressions are provided, but this is not validated as an
operational mission-analysis tool or an STK HPOP replacement. The convenience API exposes impulsive maneuvers, multi-spacecraft
propagation, bounded SMA targeting and mission scripts. Finite burns use scripts.
Estimation and STM helpers remain deferred.
Other core facilities are accessible experimentally through ``native_session``.

Licensing and distribution status
-----------------------------------

GMAT and GMAT Py code use Apache-2.0; CSPICE and embedded f2c runtime components
have their own notices. ``gmatpy/NOTICE.txt``, ``gmatpy/LICENSES.md`` and
``gmatpy/licenses/`` are included in the wheel and source archive. The component
manifests record source URLs, content hashes, applicable terms, numerical-data
reuse assessments and scientific changes. They are an engineering inventory,
not a worldwide legal guarantee. The optional archive-wide SPDX expression is
omitted for this mixed distribution; component licenses remain attached.
The responsible owner must record the product-specific export determination
required by NAIF for a CSPICE-derived product. No designation is assigned by
this package. Check an artifact::

    python python/tools/check_distribution.py dist/gmatpy-0.2.0.tar.gz
    python python/tools/check_distribution.py /path/to/gmatpy-0.2.0-*.whl --release

The first command verifies contents, notices and exclusions. ``--release`` also
fails on unresolved manifest review items, instead of presenting an unverified
bundle as cleared. Upstream reference data remain in the Git checkout/history;
the unreplaced historical ``msise90_sub.for`` source is also excluded from the
source archive. Excluding these files from wheel/sdist does not clear publication
of the entire repository. The retained CubicSpline/MSISE replacements are the
project's equation-derived implementations, with scoped numerical repairs;
their independent-origin descriptions remain project assertions. Brent uses
NASA's proposal formulas with focused safeguards. The specific baseline and
provenance decisions are recorded in ``python/ci/CORE_BASELINE.md``. They do not
establish a blanket proprietary dependency, rights clearance, or an exhaustive
audit of every inherited routine.
Choose an independent project brand and use NASA/GMAT names to identify origin.

Building and validation
-------------------------

Source builds support Linux and experimental native Windows x64/macOS
qualification paths. They require a C++17 compiler, CMake,
Ninja (or Make), CPython development headers and a PIC CSPICE archive.
SWIG and scikit-build-core are Python build requirements. Obtain the official
NAIF CSPICE toolkit and compile its C library with position-independent code,
or point ``CSPICE_DIR`` at an existing ``include/SpiceUsr.h`` /
``lib/cspice.a`` tree. The source archive does not bundle CSPICE binaries;
``python/ci/build_cspice.py`` can rebuild the recorded target-native dependency
from its pinned source archive::

    python -m pip install build 'scikit-build-core>=1.0' 'swig>=4.2,<5' auditwheel patchelf ninja
    CSPICE_DIR=/path/to/cspice bash python/tools/build_wheel.sh

``GMAT_PY_PYTHON`` selects the interpreter and ``GMAT_PY_WHEEL_DIR`` the repaired
wheel output directory. The helper builds and repairs the wheel. Building in an
older manylinux image is necessary for portable Linux wheels; repair cannot
lower a compiler's glibc requirements. For a local host-specific candidate, set
``GMAT_PY_REPAIR=0`` to retain the checked ``linux_x86_64`` wheel without a
manylinux claim. Failed builds retain their intermediate directory for diagnosis
and recovery. Direct ``python -m build --wheel`` builds
need ``-Ccmake.define.CSPICE_DIR=/path/to/cspice``. Normal GMAT builds retain the
legacy updater by default. Wheels omit duplicate unversioned linker aliases.

Experimental Windows x64 qualification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Windows build path is explicitly gated while platform qualification is
recorded. It requires an existing x64 MSVC C++17 toolchain/SDK, CMake/Ninja,
CPython development files, SWIG and the matching Windows CSPICE toolkit headers
and ``lib/cspice.lib``. An x86_64 Linux archive or Windows x64 archive cannot be
substituted for an ARM64 dependency. Use an x64 Developer Command Prompt and an
isolated Python build environment::

    python -m build --wheel --no-isolation ^
        -Ccmake.define.GMAT_PY_EXPERIMENTAL_WINDOWS=ON ^
        -Ccmake.define.CSPICE_DIR=C:/path/to/cspice

The package requires the platform-native CSPICE/f2c dependency. Windows
ARM64 is outside this path; macOS has its separate explicit architecture gate.
The Bash/auditwheel helper and ELF checker are Linux tools. From the existing
MSVC developer environment, use ``python/tools/check_windows_wheel.py`` for PE
architecture, engine DLL and imported-library checks. Install the wheel in a
fresh environment and run the package tests with no GMAT checkout/compiler/Qt
folders on PATH. Record the required Microsoft runtime dependencies and actual
CSPICE library/header hashes. The source and owner-dependent publication checks
apply to Windows candidates too.

Identifiable local candidates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use an isolated copy of the intended source inputs, retaining the original Git
revision, a full working-tree file/hash manifest and the patch layered on that
revision. A commit ID alone does not identify an uncommitted remediation tree.
Build an initial source archive, then embed its source inventory::

    python -m build --sdist --no-isolation --outdir /path/to/seed
    python python/tools/record_source.py /path/to/seed/gmatpy-0.2.0.tar.gz \
        --revision <full-git-commit> --working-tree-sha256 <manifest-sha256> \
        --output python/gmatpy/BUILD_PROVENANCE.json
    python -m build --sdist --no-isolation --outdir /path/to/candidate
    python python/tools/check_distribution.py /path/to/candidate/gmatpy-0.2.0.tar.gz \
        --source-manifest python/gmatpy/BUILD_PROVENANCE.json

Rebuild the initial archive/manifest after any source edit. Build the wheel from
the verified final source archive in a new directory. Pass the same manifest to
``check_wheel.py --source-manifest`` and record final archive/wheel SHA-256 hashes,
dependency hashes, tool versions, exact commands and new test logs. The source
digest excludes only generated ``PKG-INFO`` and the provenance file itself.
This binds the packaged inputs and copied wheel files; native correspondence
also relies on the recorded isolated build. It is not a bit-for-bit reproducible
native-build or dependency source-provenance claim. Set ``SOURCE_DATE_EPOCH`` for
repeatable archive timestamps. The wheel helper uses fresh raw, native-build and
repair directories per invocation, so old wheels in ``dist/`` cannot be selected.
The owner-dependent ``--release`` hold remains separate from candidate identity.

Install the repaired wheel in a fresh environment and run::

    python -m pip install /path/to/gmatpy-0.2.0-*.whl pytest
    python -m pytest /path/to/checkout/python/tests

``python/tools/check_wheel.py`` checks runtime dependency resolution, relocatable
library paths, no duplicate aliases and no GUI/Xerces/updater implementation.
It also checks distribution notices, inventory hashes and dataset exclusions.
Tests cover independent analytic propagation and element calculations, native
GMAT comparison, coordinate round trips and rotating velocity, time offsets,
ephemeris origins, native session lifetime/reentry, validation and concurrency.

Package contents and mission workflows
-----------------------------------------

See ``python/PROFILES.rst`` for package contents, the TLE Tailor contract,
supported impulse/multi-spacecraft/targeting/script workflows and remaining
coverage. ``gmatpy.capabilities()`` reports available features. The internal
``extended`` label is retained for compatibility; all current standard wheels
contain the full headless feature set and require no profile flags or extras.

Contributor dependencies
--------------------------

Testing and source-archive tools are in the local ``dev`` dependency group.
With uv, use ``uv sync --group dev``; this installs development tools and also
builds the project, so the native source-build prerequisites above still apply.
To obtain only contributor tools without building GMAT, use
``uv sync --group dev --no-install-project``. Pip contributors can install
``build`` and ``pytest`` explicitly in an isolated environment. Documentation
uses its separate pinned ``docs/requirements.txt``. Dependency groups are
contributor tooling, not alternate published package editions.
