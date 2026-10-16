.. _workflows:

Mission workflows and native access
===================================

GMAT Py provides a value-based Python interface over selected parts of the
bundled GMAT engine. Choose the installed profile and interface for the
calculation you need. Available SWIG classes do not establish support for every
GMAT command, plugin, or workflow.

.. _build-profiles:

Minimal and extended profiles
-----------------------------

Both profiles are builds of ``gmatpy`` version 0.2.0 and use the same import
tree. Their wheel build tags are ``1minimal`` and ``2extended``. Install an
explicit wheel filename to select a profile; Python extras do not switch
native contents. An unconstrained resolver presented with both wheels can
prefer the extended build tag. Replace a profile in an isolated environment
using ``python -m pip install --force-reinstall /path/to/profile.whl``.
The default source-build profile is extended.

Inspect the installed capabilities before selecting a workflow:

.. code-block:: python

   import gmatpy as gmat

   info = gmat.capabilities()
   print(info.profile)
   if info.supports("impulsive_maneuvers"):
       print("Scheduled impulse workflows are available")

The strings below are the exact keys accepted by
``Capabilities.supports(feature)``. Unknown keys return ``False``.

.. list-table:: Supported profile features
   :header-rows: 1
   :widths: 24 9 9 58

   * - Capability key
     - Minimal
     - Extended
     - Interface and scope
   * - ``propagation``
     - Yes
     - Yes
     - ``propagate``; forward Earth-centered Cartesian sampling.
   * - ``state_conversion``
     - Yes
     - Yes
     - ``convert_state``; supported six-component orbital representations.
   * - ``frame_conversion``
     - Yes
     - Yes
     - ``transform_state``; supported Earth-centered full-state transforms.
   * - ``time_conversion``
     - Yes
     - Yes
     - ``epoch_mjd``; supported time scales.
   * - ``native_de405``
     - Yes
     - Yes
     - ``body_state``; geometric states from bundled native DE405.
   * - ``native_session``
     - Yes
     - Yes
     - Scoped access to bundled core SWIG bindings.
   * - ``impulsive_maneuvers``
     - No
     - Yes
     - ``Impulse`` schedules used by ``propagate_mission`` and ``propagate_many``.
   * - ``multi_spacecraft``
     - No
     - Yes
     - ``propagate_many``; independent spacecraft in a common propagation setup.
   * - ``targeting``
     - No
     - Yes
     - ``target_sma``; one bounded tangential impulse solve.
   * - ``mission_scripts``
     - No
     - Yes
     - ``run_script``; trusted core mission scripts and copied output fields.
   * - ``spice_kernels``
     - No
     - Yes
     - Native SPICE bindings and bundled kernel inputs; no dedicated value-based kernel-loading helper.

Calling an unavailable convenience operation raises
``UnsupportedCapabilityError`` before native execution, with instructions for
replacing the minimal wheel. The capability set describes the supported
profile; it is not a security boundary around the raw engine.

Minimal disables SPICE source modules and wrapper classes and bundles nine
selected scientific inputs instead of extended's seventeen. It retains the
shared GMAT framework and broad core bindings, native DE405, Earth gravity,
constant-flux drag support, time/orientation data, and the restored NASA
``ICRF_Table.txt`` required by the :ref:`TLE Tailor bridge <tle-tailor>`.
The table retains NASA's original values and unequal sampling grid; the former
ERFA-generated alternative is outside the packaged defaults. JGM2 is retained as
an engine-initialization dependency even when the facade selects EGM96 or
JGM3. Minimal still has native dependencies, including CSPICE-supplied f2c
runtime objects used by MSISE. A smaller profile does not settle distribution
or licensing approval.

.. _impulsive-missions:

Schedule instantaneous maneuvers
--------------------------------

The extended profile's ``propagate_mission`` starts from one Cartesian state
and samples an orbit with native impulsive burns. Its inputs use the same
EarthMJ2000Eq frame, km, km/s, timezone-aware epoch, and propagation settings
as ``propagate``.

.. code-block:: python

   import gmatpy as gmat

   state = (7000.0, 0.0, 0.0, 0.0, 7.546053287267836, 0.0)
   samples = gmat.propagate_mission(
       state,
       "2020-07-20T12:00:00Z",
       [0.0, 600.0, 600.0, 1200.0],
       impulses=[gmat.Impulse(600.0, (0.01, 0.0, 0.0), frame="VNB")],
   )

``Impulse.time_s`` is elapsed SI seconds from the input epoch, and
``delta_v_km_s`` has three finite components. The supported burn frames are
``EarthMJ2000Eq`` and ``VNB``. The default is EarthMJ2000Eq; in VNB the first
component is along velocity. These are instantaneous velocity changes with
constant spacecraft mass.

Output times must be finite, nonnegative, and nondecreasing. They are elapsed
offsets, not integration increments. The wrapper steps to each burn, applies
it through GMAT, and synchronizes the integrator with the changed state.
Samples at a burn time are **post-burn**. Coincident burns execute in input
order, so order can matter for local frames such as VNB. Duplicate output
times repeat the same post-burn state. A burn at time zero precedes the
time-zero sample. Burns after the last requested sample, or any burn with an
empty sample schedule, are rejected.

Co-propagate independent spacecraft
-----------------------------------

``propagate_many`` accepts a nonempty mapping from spacecraft names to
EarthMJ2000Eq Cartesian states. It returns a dictionary with the same names,
each containing a list of ``Sample`` values. ``forces``, ``accuracy``, and
``max_step_s`` are common to all spacecraft. ``spacecraft`` and ``impulses``
are optional dictionaries keyed by those names; unspecified spacecraft use
default properties and have no scheduled impulses.

.. code-block:: python

   samples_by_name = gmat.propagate_many(
       {"primary": state, "comparison": state},
       "2020-07-20T12:00:00Z",
       [0.0, 600.0, 1200.0],
       spacecraft={"primary": gmat.Spacecraft(mass_kg=500.0)},
       impulses={"primary": [gmat.Impulse(600.0, (0.0, 0.01, 0.0))]},
   )

Every state must have a nonzero position. Property and impulse keys must name
an input spacecraft. All outputs are copied Python values. This workflow uses
one native propagation setup for independent trajectories; it does not enable
the optional Formation plugin or model mutual gravity and collisions.

Target one post-burn semimajor axis
-----------------------------------

``target_sma(state, epoch, target_sma_km)`` uses GMAT's DifferentialCorrector
to solve one instantaneous tangential VNB impulse. The starting state must
describe an Earth-centered elliptic orbit. The target is the post-burn
osculating semimajor axis at the input epoch, in km.

.. code-block:: python

   result = gmat.target_sma(state, "2020-07-20T12:00:00Z", 7200.0)
   print(result.delta_v_km_s, result.achieved_sma_km, result.residual_km)

``TargetResult`` also contains a copied ``final_state``. The default requested
residual is ``tolerance_km=1e-5`` and the default iteration limit is 25.
``max_iterations`` must be an integer from 1 through 100. The native solve
varies the first VNB burn component between -10 and +10 km/s with a maximum
iteration step of 0.5 km/s. After execution the wrapper independently
recomputes SMA through ``convert_state`` and raises ``RuntimeError`` if the
absolute numerical residual exceeds the requested tolerance. A positive
target does not guarantee that this bounded solve will converge.

This helper solves a single immediate orbital-element goal. Transfer timing,
multiple objectives, general trajectory optimization, and fuel minimization
need a different workflow.

.. _mission-scripts:

Run trusted scripts and finite burns
------------------------------------

``run_script`` exposes selected core mission-sequence workflows without
requiring a dedicated Python wrapper for each command:

.. code-block:: python

   result = gmat.run_script(
       "mission.script", outputs={"Sat": ["X", "Y", "Z", "TotalMass"]}
   )
   mass_kg = float(result["Sat"]["TotalMass"])

``path`` must exist. ``outputs`` maps runtime object names to sequences of
field names; a single string is not a field sequence. Results are nested
dictionaries of copied native ``GetField`` **strings**, so convert fields to
numbers explicitly when appropriate. A missing runtime object raises
``ValueError``. Failure to load or complete a script raises ``RuntimeError``;
native field access can also raise native API exceptions. Native objects are
cleared on exit, including after an error.

Run only scripts you trust: GMAT scripts can write files and execute command
loops. This interface provides neither a sandbox nor a promise that arbitrary
GMAT scripts or optional plugins will work. Use a temporary or dedicated
working location and control the paths referenced by your script.

Finite-duration thrust with tank mass depletion is available through trusted
core scripts in the extended profile. A script creates ``ChemicalTank``,
``ChemicalThruster``, and ``FiniteBurn`` objects, attaches them to the
spacecraft, and brackets propagation with ``BeginFiniteBurn`` and
``EndFiniteBurn``. The repository's
`finite-burn regression <https://github.com/dcajacob/gmatpy/blob/50f61a05a1dd68ba2682d74a8631eba1b514630e/python/tests/test_finite_burn.py>`_
checks a ten-second constant-thrust case against expected mass flow and
velocity change. There is no high-level finite-burn/tank facade. The
``Impulse`` and ``Spacecraft`` convenience values retain constant-mass
semantics.

.. _native-access:

Use the native API within its lifetime
--------------------------------------

For core facilities outside the convenience interface, ``native_session``
supplies bundled SWIG bindings with runtime setup, serialization, and object
cleanup:

.. code-block:: python

   with gmat.native_session() as api:
       sat = api.Construct("Spacecraft", "InspectionSat")
       sat.SetField("DryMass", 125.0)
       dry_mass = float(sat.GetField("DryMass"))
       del sat
   print(dry_mass)

Copy values while the session is active. Native handles such as ``sat``
belong to the session and must never be used afterward. Entering and leaving
the session clears configured native objects, including on exceptions.
Calling a convenience function that enters the engine or opening another
native session from inside an active session raises ``RuntimeError``.
The metadata-only ``capabilities()`` call does not enter the engine.

Raw SWIG access retains GMAT's native ownership rules. A receiving native
object can take ownership of another object, and SWIG's ``thisown`` flag
controls Python ownership. Incorrect transfers can cause double deletion or
invalid handles; copying a Python reference does not extend the native
lifetime. Follow the ownership pattern for the specific native API instead
of setting ``thisown`` indiscriminately. For example, the facade creates an
unregistered atmosphere, attaches it to a drag force, and relinquishes Python
ownership after successful attachment. Registering that same atmosphere
with ``Construct`` would introduce an additional native owner.

The bundled engine has process-global state. Calls from multiple threads
serialize, including script execution and native sessions. Use
``multiprocessing.get_context("spawn")`` for independent parallel workers.
Using GMAT Py after ``fork`` is rejected. Keep a separately installed GMAT
Python API in a separate process and virtual environment: it shares the
``gmatpy`` import name and must not coexist with this bundled engine in one
process.

.. _native-spice-cleanup:

SPICE kernel cleanup is process-global
--------------------------------------

The extended native API exposes ``SpiceInterface``. Its CSPICE kernel pool is
shared by the whole process, including other libraries that call CSPICE.
``native_session`` serializes GMAT access and clears configured GMAT objects;
it does not create a private kernel pool or isolate external pool owners.

``UnloadKernel(path)`` retains NASA's individual-unload behavior. If CSPICE
reports an unload error, GMAT prints a warning, resets CSPICE's error flag,
removes the kernel from its own loaded-file cache, and can still return
``True``. That return value therefore does not prove that a failed unload
reconstructed a usable pool. The method does not clear the entire pool and
replay unrelated kernels. ``IsLoaded`` checks GMAT's cache, not every kernel
or value present in CSPICE. A partly failed meta-kernel load can leave child
kernel state in CSPICE that the cache does not track.

``UnloadAllKernels()`` is an explicit full reset using CSPICE ``kclear_c``.
It can clear the pool even when previously loaded text-kernel files have
vanished and cannot be reread. It also removes **externally furnished kernels
and directly inserted pool values**, then clears GMAT's loaded-file cache.
This operation has no private-ownership boundary. Coordinate a full reset and
any required reloads with every user of the process-global pool, or run
independent native work in separate spawned processes.

The extended profile includes the restored March 2026 Earth high-precision
PCK snapshot, whose coverage ends on 2026-06-12; its
``earth_latest_high_prec.bpc`` alias does not mean it is a current download.
Implemented nutation coefficients retain NASA's original summation order.
These restored scientific inputs do not enlarge the facade's frame or
mission coverage. See :doc:`conventions` for the individual data limits.

The restored source candidate has fresh native qualification for Linux
x86_64, CPython 3.14.7, in both profiles. Previous Linux ARM64 and macOS
results concern the older source and do not qualify the restored candidate.
Read :ref:`platform-support` for the current source and artifact boundaries.

Deferred coverage
-----------------

``capabilities().deferred_plugins`` currently reports
``estimation/ekf``, ``station/measurement``, ``tle_propagator``,
``external_force_callbacks``, ``optional_optimizers``, ``csalt``, ``matlab``,
``gmat_functions``, and ``gui``. These plugin families are not enabled by
installing the extended wheel. Optional ephemeris-propagator plugins are also
outside the supported facade.

Dedicated value-based STM/covariance helpers, finite burns/tanks, maneuvers
with mass depletion, general multi-goal targeting, additional gravity
bodies/models, and full C++ binding parity remain future work. Script-level
finite burns above are a specific supported core case. Raw bindings may
expose other core classes experimentally; that exposure is not complete GMAT
coverage or evidence of numerical equivalence to a NASA GMAT release.

The supported boundary is defined by the
`profile specification <https://github.com/dcajacob/gmatpy/blob/50f61a05a1dd68ba2682d74a8631eba1b514630e/python/PROFILES.rst>`_,
the facade, and its regression tests.
