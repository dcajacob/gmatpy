GMAT Py build profiles and mission coverage
==========================================

Two wheel variants use the same project name/version and ``import gmatpy``.
``minimal`` has wheel build tag ``1minimal``; ``extended`` has ``2extended``.
Install one explicit wheel path in an isolated environment. Use ``python -m pip install --force-reinstall /path/to/profile.whl`` to
switch variants of the same version. This replaces the same distribution; do not create separate distributions
that both own this namespace. Pip cannot select these profiles using extras.
When both wheel files are available to an unconstrained resolver, its wheel
build-tag preference can select extended; specify the minimal file explicitly.
The default source build remains extended for existing native-API callers.

Build with ``GMAT_PY_PROFILE=minimal`` or ``extended`` using
``python/tools/build_wheel.sh``. ``GMAT_PY_BUILD_DIR`` optionally selects a
persistent, isolated native build directory; never share it between profiles.
Direct build frontends must set both ``cmake.define.GMAT_PY_PROFILE`` and
``wheel.build-tag`` (``1minimal`` / ``2extended``). ``GMAT_PY_REPAIR=0`` selects a
local Linux wheel; it does not establish manylinux compatibility.

The minimal profile is a real C++/data build variant. It disables
``GMAT_ENABLE_SPICE``, omits SPICE source modules and wrapper classes, and ships
nine selected scientific inputs instead of seventeen. Native DE405 remains
because the default propagation force model needs Sun/Moon ephemerides. The
ICRF orientation table remains because TLE Tailor requires the full six-state
MJ2000Eq/ICRF transformation before its Astropy TEME bridge. Earth gravity,
constant-flux drag, time, EOP and nutation data remain. JGM2 also remains because
the inherited force-model factory opens it during default object construction,
before the facade selects EGM96 or JGM3. It is an initialization dependency. Removing those inputs or
relabeling frames would change the existing TLE Tailor contract.

Minimal still includes the shared GMAT framework and broad core SWIG bindings;
it is not a rewrite containing only an integrator. Its underlying core can have
methods beyond the supported convenience surface. Capability reporting describes
the supported profile, not a security boundary. CSPICE-supplied f2c runtime
objects remain linked for MSISE; keep their terms and the existing release hold.
Omitting kernel support is not an export/legal clearance.

Both profiles retain the existing propagation, state/time/frame conversion,
native DE405 ephemeris helpers, and scoped ``native_session``. Existing imports
and ordinary ``ForceModel`` / ``Spacecraft`` settings are preserved. Inspect
``gmatpy.capabilities()`` and ``.supports(feature)`` before selecting a workflow.
A profile-unavailable convenience operation raises ``UnsupportedCapabilityError``
with replacement-install guidance before entering the native engine.

The extended profile adds these supported value-based operations:

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
GMAT functions and GUI remain deferred. High-level finite-duration burn/tank
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
