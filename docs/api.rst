Python API reference
====================

.. py:module:: gmatpy

This page documents every name exported by ``gmatpy.__all__`` in version 0.2.0.
Import them from ``gmatpy``. The reference describes the value-based interface;
the broader SWIG interface is reached through :func:`native_session`.
See :doc:`conventions` for the shared time, frame and unit contracts.

``minimal`` and ``extended`` expose the same Python names. Availability below
describes the installed native profile, not whether a name can be imported.

Common error behavior
---------------------

Numeric inputs must be finite; the scalar/vector validators reject booleans,
NaN and infinity. Scalar inputs accepted by those validators are converted with
``float()``. Names of formats, frames, bodies, scales and features are
case-sensitive. Validation errors normally raise :class:`ValueError`; wrong
configuration object types raise :class:`TypeError` as listed below.

Engine operations can also raise :class:`RuntimeError` on initialization,
missing bundled scientific data, failed native operations, non-finite native
results, calls after ``fork``, or entry from an active native session. Native
errors may propagate as the SWIG API's ``APIException`` (a Python exception);
the facade does not translate every native failure into one exception type.
Unsupported mission workflows raise :exc:`UnsupportedCapabilityError` before
entering the engine. See :func:`native_session` for lifetime and concurrency
rules, and :doc:`conventions` for scientific data limits.

Propagation configuration and results
-------------------------------------

.. py:class:: Spacecraft(mass_kg=1000.0, drag_area_m2=1.0, srp_area_m2=1.0, cd=2.2, cr=1.8)

   Frozen dataclass containing constant spacecraft properties. Available in
   both profiles. The propagation wrappers use spherical drag/SRP models.

   :param float mass_kg: Positive dry mass in kg.
   :param float drag_area_m2: Nonnegative drag area in m².
   :param float srp_area_m2: Nonnegative solar-radiation-pressure area in m².
   :param float cd: Positive dimensionless drag coefficient.
   :param float cr: Positive dimensionless reflectivity coefficient.
   :raises ValueError: A property is non-finite or outside its range.

   Validated numeric fields are stored as floats. No mass consumption is
   modeled by the value-based propagation or impulse wrappers.

   .. py:attribute:: mass_kg
      :type: float
      :value: 1000.0

   .. py:attribute:: drag_area_m2
      :type: float
      :value: 1.0

   .. py:attribute:: srp_area_m2
      :type: float
      :value: 1.0

   .. py:attribute:: cd
      :type: float
      :value: 2.2

   .. py:attribute:: cr
      :type: float
      :value: 1.8

.. py:class:: ForceModel(gravity_model="EGM96", degree=8, order=None, sun=True, moon=True, srp=True, drag=False, f107=150.0, f107a=150.0, kp=3.0)

   Frozen dataclass selecting Earth gravity and optional perturbations.
   Available in both profiles.

   :param str gravity_model: ``"EGM96"`` (degree/order through 360) or
      ``"JGM3"`` (through 70).
   :param int degree: Gravity degree, from 0 through the selected model's limit.
      Zero selects a monopole.
   :param order: Gravity order, from 0 through ``degree``; ``None`` uses
      ``degree``. Stored as the resolved integer after construction.
   :type order: int or None
   :param bool sun: Include Sun point-mass gravity, using native DE405.
   :param bool moon: Include lunar point-mass gravity, using native DE405.
   :param bool srp: Include spherical solar radiation pressure.
   :param bool drag: Include Jacchia-Roberts atmospheric drag with constant
      solar-flux and geomagnetic indices.
   :param float f107: Positive daily F10.7 solar flux, in solar flux units.
   :param float f107a: Positive average F10.7 solar flux, in solar flux units.
   :param float kp: Constant Kp index, from 0 through 9 inclusive.
   :raises ValueError: Unsupported gravity model, invalid integer degree/order,
      non-boolean switches, or invalid scalar properties.

   With ``degree=0`` and ``drag=False``, the wrapper creates a native point-mass
   force. With drag enabled it uses a degree/order-zero gravity field to supply
   the primary-body dependency; this still supplies the monopole. No weather
   file is read by this configuration.

   .. py:attribute:: gravity_model
      :type: str
      :value: "EGM96"

   .. py:attribute:: degree
      :type: int
      :value: 8

   .. py:attribute:: order
      :type: int

      Resolved order; defaults to 8 when ``degree`` is unchanged.

   .. py:attribute:: sun
      :type: bool
      :value: True

   .. py:attribute:: moon
      :type: bool
      :value: True

   .. py:attribute:: srp
      :type: bool
      :value: True

   .. py:attribute:: drag
      :type: bool
      :value: False

   .. py:attribute:: f107
      :type: float
      :value: 150.0

   .. py:attribute:: f107a
      :type: float
      :value: 150.0

   .. py:attribute:: kp
      :type: float
      :value: 3.0

.. py:class:: Sample(time_s, position_km, velocity_km_s)

   Frozen result dataclass, available in both profiles. Propagation functions
   populate it with copied Python values in ``EarthMJ2000Eq``. Direct
   construction does not validate or normalize the fields.

   :param float time_s: Elapsed SI seconds from the input epoch.
   :param position_km: Cartesian position, a three-float tuple in km.
   :param velocity_km_s: Cartesian velocity, a three-float tuple in km/s.

   .. py:attribute:: time_s
      :type: float

   .. py:attribute:: position_km
      :type: tuple[float, float, float]

   .. py:attribute:: velocity_km_s
      :type: tuple[float, float, float]

   .. py:property:: state
      :type: tuple[float, ...]

      Concatenates ``position_km + velocity_km_s`` into a six-component
      Cartesian tuple.

.. py:function:: propagate(state, epoch, times, *, forces=None, spacecraft=None, accuracy=1e-12, max_step_s=60.0)

   Start a fresh Earth-centered orbit and sample native Prince-Dormand 7/8
   integration. Available in both profiles.

   :param state: Iterable of six finite Cartesian components
      ``[x, y, z, vx, vy, vz]`` in ``EarthMJ2000Eq`` (km, km/s).
      The position must be nonzero.
   :param epoch: Timezone-aware ``datetime`` or ISO 8601 string with a timezone.
   :param times: Iterable of finite, nonnegative elapsed SI seconds from
      ``epoch``, in nondecreasing order. These are output epochs, not step sizes.
   :param forces: :class:`ForceModel`, or ``None`` for ``ForceModel()``.
   :param spacecraft: :class:`Spacecraft`, or ``None`` for ``Spacecraft()``.
   :param float accuracy: Positive native integrator accuracy setting; it is
      not a guaranteed position/velocity error bound.
   :param float max_step_s: Positive maximum integration step in seconds.
   :returns: One :class:`Sample` per requested time, including duplicates.
      Empty ``times`` returns ``[]`` after input validation.
   :rtype: list[Sample]
   :raises ValueError: Invalid state, epoch, times, accuracy or step limit.
   :raises TypeError: ``forces`` or ``spacecraft`` has the wrong type.
   :raises RuntimeError: Integration fails, yields an invalid state, or the
      requested time cannot be advanced at floating-point resolution.

   A sample at zero is the input state. Each call owns a fresh setup and clears
   its native objects on completion or error. Engine access is serialized.

State, frame, time and ephemeris utilities
------------------------------------------

.. py:function:: convert_state(state, from_type="Cartesian", to_type="Keplerian", *, mu=None, anomaly="TA")

   Convert a six-component orbital representation with GMAT's native state
   conversion routines. Available in both profiles.

   :param state: Iterable of six finite numbers in ``from_type`` ordering.
   :param str from_type: Input representation.
   :param str to_type: Output representation. Supported values for both
      arguments are ``Cartesian``, ``Keplerian``, ``ModifiedKeplerian``,
      ``Equinoctial``, ``ModifiedEquinoctial``, ``SphericalRADEC`` and
      ``SphericalAZFPA``.
   :param mu: Positive central-body gravitational parameter in km³/s²,
      or ``None`` to use GMAT's Earth value.
   :type mu: float or None
   :param str anomaly: ``"TA"`` (true), ``"MA"`` (mean), ``"EA"``
      (eccentric) or ``"HA"`` (hyperbolic) anomaly for representations
      using an anomaly. Not every choice is valid for every conic.
   :returns: Six Python floats in ``to_type`` ordering.
   :rtype: tuple[float, ...]
   :raises ValueError: Invalid vector, format, anomaly token or ``mu``.
   :raises RuntimeError: Native output is non-finite.

   Representation layouts and units are in :ref:`state-representations`.
   A custom ``mu`` changes the two-body conversion parameter; it does not
   select a new force model, origin or frame. The call still passes Earth's
   flattening and equatorial radius to the native routine. Singular or
   physically invalid element sets may raise a native ``APIException``.

.. py:function:: transform_state(state, epoch, *, from_frame="EarthMJ2000Eq", to_frame="EarthFixed")

   Transform the full Cartesian position **and velocity** between supported
   Earth-centered frames. Available in both profiles.

   :param state: Iterable of six finite Cartesian numbers, in km and km/s.
   :param epoch: Timezone-aware ``datetime`` or ISO 8601 string with a timezone.
   :param str from_frame: Input frame.
   :param str to_frame: Output frame. Both accept ``EarthMJ2000Eq``,
      ``EarthMJ2000Ec``, ``EarthICRF`` or ``EarthFixed``.
   :returns: A copied six-component Cartesian tuple in ``to_frame``.
   :rtype: tuple[float, ...]
   :raises ValueError: Invalid vector, epoch or frame token.
   :raises RuntimeError: Native coordinate conversion fails or is non-finite.

   ``EarthFixed`` includes rotating-frame velocity terms and uses GMAT's
   FK5/IAU1980 convention; do not label it ITRF or TEME. For the inherited
   FK5/MJ2000Eq-to-ICRF base conversion, the same interpolated matrix rotates
   position and velocity and the base rotation derivative is zero.

   ``EarthICRF`` uses the exact original ``ICRF_Table.txt`` from the pinned
   NASA baseline, with its irregular grid and gaps up to 16 days. Native
   ninth-order Lagrange interpolation spans internal gaps; the table endpoints
   bound supported epochs. This is not the former ERFA-generated alternative.
   See :doc:`conventions` for exact date limits and the separate extended
   SPICE Earth-PCK limit; that PCK is not the default EarthFixed rotation model.

.. py:function:: epoch_mjd(epoch, scale="UTC")

   Express an input UTC instant as conventional Modified Julian Date in a
   selected time scale. Available in both profiles.

   :param epoch: Timezone-aware ``datetime`` or ISO 8601 string with a timezone.
   :param str scale: ``UTC``, ``TAI``, ``TT``, ``TDB``, ``UT1`` or GMAT's ``A1``.
   :returns: MJD using ``JD - 2400000.5``, in days in the requested scale.
   :rtype: float
   :raises ValueError: Invalid epoch or scale token.

   Offset-bearing input strings are normalized to UTC. The result does not
   expose GMAT's internal ModJulian origin. Python datetime precision and the
   bundled leap-second/EOP snapshots apply; literal ``23:59:60`` input is
   unsupported.

.. py:function:: body_state(body, epoch, *, origin="Earth")

   Obtain a geometric ephemeris six-state with native DE405, available in
   both profiles.

   :param str body: ``Sun``, ``Mercury``, ``Venus``, ``Earth``, ``Luna``
      (or alias ``Moon``), ``Mars``, ``Jupiter``, ``Saturn``, ``Uranus``,
      ``Neptune`` or ``Pluto``.
   :param epoch: Timezone-aware ``datetime`` or ISO 8601 string with a timezone.
   :param str origin: Reference body, accepting the same body set and alias.
   :returns: ``body - origin`` in MJ2000Eq axes, position in km and velocity
      in km/s. Identical body and origin yield a zero six-state.
   :rtype: tuple[float, ...]
   :raises ValueError: Unsupported body/origin or invalid epoch.
   :raises RuntimeError: Native state is non-finite.

   No light-time or aberration correction is applied. Requests outside the
   bundled DE405 interval may raise a native exception. This helper does not
   depend on the extended profile's SPICE kernel readers.

Mission workflows
-----------------

The following functions require the extended profile. Their result objects
and :class:`Impulse` can be imported and constructed in either profile.

.. py:class:: Impulse(time_s, delta_v_km_s, frame="EarthMJ2000Eq")

   Frozen dataclass defining an instantaneous, constant-mass maneuver.

   :param float time_s: Finite, nonnegative elapsed SI seconds from the initial
      propagation epoch.
   :param delta_v_km_s: Iterable of three finite delta-v components in km/s;
      stored as a tuple of floats.
   :param str frame: ``"EarthMJ2000Eq"`` or local ``"VNB"``.
   :raises ValueError: Invalid burn time, vector length/components or frame.
   :raises TypeError: ``delta_v_km_s`` is not iterable.

   VNB components follow velocity, orbit normal and their right-handed
   binormal, evaluated at the maneuver. No tank or mass depletion is modeled.

   .. py:attribute:: time_s
      :type: float

   .. py:attribute:: delta_v_km_s
      :type: tuple[float, float, float]

   .. py:attribute:: frame
      :type: str
      :value: "EarthMJ2000Eq"

.. py:function:: propagate_mission(state, epoch, times, *, impulses=(), forces=None, spacecraft=None, accuracy=1e-12, max_step_s=60.0)

   Propagate one spacecraft with scheduled native impulsive maneuvers.
   Requires ``impulsive_maneuvers`` (extended).

   :param state: Six-component initial Cartesian state as in :func:`propagate`.
   :param epoch: Timezone-aware initial epoch as in :func:`propagate`.
   :param times: Nonnegative, nondecreasing elapsed seconds as in
      :func:`propagate`.
   :param impulses: Iterable of :class:`Impulse` objects, all at or before
      the final requested output time. Default: no maneuvers.
   :param forces: :class:`ForceModel` or ``None`` for the default model.
   :param spacecraft: :class:`Spacecraft` or ``None`` for default properties.
   :param float accuracy: Positive native integrator accuracy setting.
   :param float max_step_s: Positive maximum integration step in seconds.
   :returns: One :class:`Sample` per output time. Burn-time samples are
      post-burn. Equal-time burns retain input order; duplicate output times
      repeat the post-burn state. Empty times with no burns returns ``[]``.
   :rtype: list[Sample]
   :raises UnsupportedCapabilityError: The installed profile is minimal.
   :raises ValueError: Invalid propagation input or a burn beyond the sampled
      interval (including any burn with empty output times).
   :raises TypeError: Invalid forces, spacecraft or impulse object types.
   :raises RuntimeError: Native integration or maneuver fails.

.. py:function:: propagate_many(states, epoch, times, *, forces=None, spacecraft=None, impulses=None, accuracy=1e-12, max_step_s=60.0)

   Co-propagate named spacecraft in one native propagator. Requires
   ``multi_spacecraft`` (extended). This uses the core propagator, without
   the optional Formation plugin or spacecraft mutual gravity/collisions.

   :param states: Nonempty mapping of nonempty string names to six-component
      ``EarthMJ2000Eq`` Cartesian states (km, km/s), with nonzero positions.
   :param epoch: Shared timezone-aware initial epoch.
   :param times: Shared iterable of nonnegative, nondecreasing elapsed seconds.
   :param forces: Shared :class:`ForceModel`, or ``None`` for the default.
   :param spacecraft: Optional mapping of state names to :class:`Spacecraft`
      values. Missing names receive default properties.
   :param impulses: Optional mapping of state names to iterables of
      :class:`Impulse` objects. Missing names receive no burns.
   :param float accuracy: Positive native integrator accuracy setting.
   :param float max_step_s: Positive maximum integration step in seconds.
   :returns: Mapping with the input names, each containing one :class:`Sample`
      per output time. Empty times with no burns returns each name mapped to
      ``[]``. Samples at maneuvers are post-burn.
   :rtype: dict[str, list[Sample]]
   :raises UnsupportedCapabilityError: The installed profile is minimal.
   :raises ValueError: Invalid states/names/times, unknown names in the optional
      mappings, or a burn beyond the final sample.
   :raises TypeError: Invalid force, spacecraft or impulse object types.
   :raises RuntimeError: Native integration, maneuver or state extraction fails.

   Burns are sorted by time. Ties retain their traversal order: the order of
   keys in the impulse mapping, then the order within each spacecraft schedule.
   Common forces do not imply identical spacecraft areas or mass.

.. py:class:: TargetResult(delta_v_km_s, final_state, achieved_sma_km, residual_km)

   Frozen result dataclass returned by :func:`target_sma`. Direct construction
   does not validate or normalize fields.

   :param float delta_v_km_s: Solved signed tangential VNB delta-v in km/s.
   :param final_state: Post-burn Cartesian six-tuple in ``EarthMJ2000Eq``
      (km, km/s) at the input epoch.
   :param float achieved_sma_km: SMA calculated from ``final_state`` in km.
   :param float residual_km: ``achieved_sma_km - target_sma_km``.

   .. py:attribute:: delta_v_km_s
      :type: float

   .. py:attribute:: final_state
      :type: tuple[float, ...]

   .. py:attribute:: achieved_sma_km
      :type: float

   .. py:attribute:: residual_km
      :type: float

.. py:function:: target_sma(state, epoch, target_sma_km, *, tolerance_km=1e-5, max_iterations=25)

   Solve an instantaneous tangential VNB burn with GMAT's
   ``DifferentialCorrector``. Requires ``targeting`` (extended).

   :param state: Six finite ``EarthMJ2000Eq`` Cartesian components (km, km/s)
      describing an Earth-centered elliptic initial orbit.
   :param epoch: Timezone-aware initial epoch.
   :param float target_sma_km: Positive target post-burn semi-major axis in km.
   :param float tolerance_km: Positive maximum accepted absolute SMA residual
      in km, independently checked after the native solve.
   :param int max_iterations: Integer from 1 through 100 inclusive;
      booleans are rejected.
   :returns: Burn and post-burn state at the input epoch.
   :rtype: TargetResult
   :raises UnsupportedCapabilityError: The installed profile is minimal.
   :raises ValueError: Invalid vector/epoch, non-elliptic initial orbit,
      invalid target/tolerance or iteration count.
   :raises RuntimeError: Script execution fails or the final residual exceeds
      ``tolerance_km``.

   Only VNB component 1 varies; the other components remain zero. The native
   solve bounds the signed burn to [-10, 10] km/s, with a maximum iteration
   change of 0.5 km/s. There is no coast interval, transfer-time solve, mass
   depletion or general fuel/multi-goal optimization.

.. py:function:: run_script(path, *, outputs)

   Run a trusted core GMAT mission script and copy selected runtime fields.
   Requires ``mission_scripts`` (extended).

   :param path: Filesystem path accepted by ``pathlib.Path``. ``~`` is expanded;
      the path is resolved with ``strict=True`` before loading.
   :param outputs: Mapping of nonempty runtime object names to iterables of
      nonempty field-name strings. A bare string is not a field sequence.
   :returns: Nested ``{object_name: {field_name: value_string}}`` dictionary.
      Values are native ``GetField`` strings; the wrapper does not parse units,
      numbers or arrays. An empty mapping requests execution without fields.
   :rtype: dict[str, dict[str, str]]
   :raises UnsupportedCapabilityError: The installed profile is minimal.
   :raises OSError: Path resolution fails, including a missing file.
   :raises TypeError: ``outputs`` is not a mapping, or a field list is a string
      or cannot be iterated.
   :raises ValueError: Empty/invalid object or field names, or a requested
      runtime object does not exist.
   :raises RuntimeError: Native script loading or execution reports failure.

   Native field lookup can raise ``APIException``. The wrapper clears owned
   native objects even if loading, execution or field extraction fails.
   Scripts can write files and run command loops. Use scripts you trust; this
   interface is not a sandbox. Core finite-burn and targeting commands can be
   used when configured correctly; optional-plugin and arbitrary GMAT script
   compatibility are outside this contract.

Capabilities and native access
------------------------------

.. py:class:: Capabilities(profile, features, deferred_plugins)

   Frozen dataclass describing supported installation capabilities. Available
   in both profiles. :func:`capabilities` supplies normalized values; direct
   dataclass construction does not validate the fields.

   :param str profile: ``"minimal"`` or ``"extended"`` for installed builds.
   :param features: Frozen set of feature tokens.
   :param deferred_plugins: Tuple of deferred plugin-family tokens.

   .. py:attribute:: profile
      :type: str

   .. py:attribute:: features
      :type: frozenset[str]

   .. py:attribute:: deferred_plugins
      :type: tuple[str, ...]

   .. py:method:: supports(feature)

      :param str feature: Case-sensitive feature token.
      :returns: Whether ``feature`` belongs to :attr:`features`. Unknown string
         tokens return ``False``.
      :rtype: bool

.. py:function:: capabilities()

   Read the installed ``BUILD_PROFILE.json`` without initializing the engine.
   If the file is absent in a source overlay, the implementation defaults to
   ``extended``; this fallback does not verify built native artifacts.

   :returns: Installed profile and supported feature/deferred-plugin sets.
   :rtype: Capabilities
   :raises RuntimeError: The profile token is neither minimal nor extended.

   Both profiles report ``propagation``, ``state_conversion``,
   ``frame_conversion``, ``time_conversion``, ``native_de405`` and
   ``native_session``. Extended also reports ``impulsive_maneuvers``,
   ``multi_spacecraft``, ``targeting``, ``mission_scripts`` and ``spice_kernels``.

   The deferred plugin tuple is ``estimation/ekf``, ``station/measurement``,
   ``tle_propagator``, ``external_force_callbacks``, ``optional_optimizers``,
   ``csalt``, ``matlab``, ``gmat_functions`` and ``gui``. Reporting describes
   the supported build surface; it is not a security boundary or a complete
   inventory of every underlying C++ method.

.. py:exception:: UnsupportedCapabilityError

   Subclass of :class:`RuntimeError` raised by a convenience mission operation
   unavailable in the selected profile. The message advises replacing the
   minimal wheel with an explicit extended wheel using ``--force-reinstall``.
   Both variants own the same ``gmatpy`` distribution and import tree.

.. py:function:: native_session()

   Context manager giving access to the bundled core's existing SWIG module.
   Available in both profiles; minimal omits SPICE classes and kernel support.

   :returns: A context manager whose ``with ... as api`` value is the native
      GMAT API module. Configure and use all native objects inside that block.
   :raises RuntimeError: Initialization fails, data are missing, a native
      operation is nested in this thread, or the process was forked after
      importing the runtime.

   Setup, serialization and ``Clear()`` cleanup are automatic. Every native
   object handle belongs to the session and becomes invalid when it exits,
   including exceptional exit. Do not retain handles or dereference them later.
   Return copied Python values from your own adapter instead.

   Convenience functions that enter the native engine and nested sessions are
   rejected inside an active session in the same thread. Engine operations
   across threads are serialized. Use ``multiprocessing.get_context("spawn")``
   for independent parallel work; calling after ``fork`` is rejected. Do not
   load another GMAT installation/API in the same process.

   Raw bindings retain GMAT's native ownership rules, including ownership
   transfer when attaching some objects. Scoped cleanup does not remove that
   responsibility. GUI and optional-plugin APIs are unavailable, and the
   existence of a SWIG symbol does not establish supported or qualified behavior.
   Startup files and logs use a private temporary directory. Value-based
   helpers preserve the caller's working directory.

   In extended, the SPICE kernel pool is process-global. The native
   ``UnloadAllKernels()`` operation clears the entire pool, including kernels
   or inserted values furnished outside that interface; coordinate ownership
   with other SPICE users. An individual ``UnloadKernel()`` failure retains
   the inherited warning/recovery limitations and does not promise pool
   reconstruction or isolation. The bundled March Earth PCK ends at
   2026-06-12 even though the separate EOP snapshot extends to September.
