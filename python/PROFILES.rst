GMAT Py package contents and mission coverage
==============================================

GMAT Py ships one complete headless Python library. The standard wheel contains
its native engine, SWIG bindings, all seventeen curated scientific inputs,
SPICE support and the supported mission helpers below. There are no minimal
and extended distributions, variant build tags or optional feature extras.
The historical ``extended`` token remains in ``BUILD_PROFILE.json`` and
``gmatpy.capabilities().profile`` for API compatibility; it is not an install
choice. No GUI is included or planned for this package.

Build the standard wheel with ``python/tools/build_wheel.sh`` and a matching
``CSPICE_DIR``. Direct build frontends need no profile or wheel build-tag flags.
``GMAT_PY_BUILD_DIR`` optionally selects a persistent isolated native build
directory. ``GMAT_PY_REPAIR=0`` selects a local Linux wheel; it does not establish
manylinux compatibility. Obsolete minimal-profile overrides are rejected.

Propagation, state/time/frame conversion, native DE405 ephemeris helpers and
scoped ``native_session`` are always available. Sun/Moon ephemerides, the ICRF
orientation table, EOP/nutation/time inputs and gravity data retain their exact
scientific values and coverage limits. The source/data inventory and component
notices remain attached. CSPICE and embedded f2c have their separate terms;
the owner-dependent product export-determination item remains unresolved.

The package includes these supported value-based mission operations:

* ``propagate_mission(state, epoch, times, impulses=[Impulse(...)])`` uses native
  impulsive burns and synchronizes the propagator across velocity discontinuities.
  Delta-v is km/s in EarthMJ2000Eq or VNB. Mass is constant. Samples at burn times
  are post-burn; simultaneous burns retain input order and duplicate times repeat
  the same post-burn state.
* ``propagate_many({name: state, ...}, epoch, times, ...)`` puts independent
  spacecraft into one native propagation setup with common forces, individual
  spacecraft properties, and optional per-spacecraft impulse schedules. This is
  not the excluded Formation plugin and does not model mutual gravity/collisions.
* ``target_sma`` uses GMAT's DifferentialCorrector to solve one tangential VNB
  impulse for post-burn Earth-centered SMA. It bounds iterations and verifies the
  achieved numerical residual. This is not a general transfer/fuel optimizer.
* ``run_script(path, outputs={object: [field, ...]})`` loads/runs a trusted core
  mission script and returns copied runtime field strings. It retains native
  object cleanup on errors. It can execute native targeting/finite-burn commands
  without dedicated value-based wrappers. A script can write files or contain
  loops; this is not a sandbox or universal GMAT-script compatibility claim.

All calls obey GMAT's global-state serialization and native-session lifetime
rules. Parallel work uses spawned processes. Optional plugin families are not
newly enabled: estimation/EKF, station/measurement, TLE/ephemeris plugin
propagators, external-force/Python callbacks, optional optimizers, CSALT, MATLAB,
GMAT functions remain deferred. GUI support is outside this package's scope. High-level finite-duration burn/tank
models, STM/covariance, general multi-goal targeting, maneuvers with mass depletion,
additional gravity bodies/models and full C++ binding parity remain future work.

TLE Tailor contract checked from its adapter/tests
-------------------------------------------------

``tle_tailor/propagation/gmatpy.py`` forwards Cartesian km/km/s state,
timezone-aware epoch, nonnegative nondecreasing elapsed SI seconds (including
duplicates), forces, spacecraft, accuracy and maximum step. It requires
``propagate`` plus ``transform_state`` in both MJ2000Eq/ICRF directions. It uses
Astropy for TEME/ITRS/GCRS, velocity frame terms and offline IERS handling, returns
UTC timestamps and finite arrays shaped (N,2,3), and rejects leap-second-crossing
intervals. It does not require GMAT's TLE plugin, SPICE kernel readers, GUI,
Space-Track credentials or live data downloads. Its native physics tests also
use ``native_session`` to obtain Earth's GMAT gravitational constant.
