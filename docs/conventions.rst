Time, frames, units and scientific inputs
=========================================

Use these conventions when handing states between GMAT Py and other tools.
The value-based functions return copied Python numbers; they do not carry
unit, frame or time-scale metadata with each vector. The caller must keep
that context.

Epochs and elapsed time
-----------------------

An input epoch is a timezone-aware ``datetime`` or an ISO 8601 string accepted
by Python's ``datetime.fromisoformat`` with a timezone. For example,
``"2020-07-20T12:00:00Z"`` and ``"2020-07-20T06:00:00-06:00"`` describe the
same instant. Naive datetimes and strings without a timezone are rejected.
Inputs are normalized to UTC, preserving Python datetime's microsecond
precision before conversion to native time. Native floating-point calculations
can still limit effective precision.

Propagation ``times`` and impulse ``time_s`` are **elapsed SI seconds from the
initial epoch**. They are not UTC timestamps or incremental steps. Output times
must be finite, nonnegative and nondecreasing. Duplicate times are allowed.
An empty output sequence returns no samples, after validation. Backward
propagation is outside the value-based interface.

The orbital integrator advances the supplied SI duration. Civil UTC arithmetic
across a leap second needs care: Python datetime cannot represent
``23:59:60``, and the interface does not provide a leap-second timestamp type.
If another system constructs UTC output timestamps by adding timedeltas, verify
its leap-second behavior. TLE Tailor's adapter rejects leap-second-crossing
intervals as part of its own contract.

:func:`gmatpy.epoch_mjd` returns conventional MJD, ``JD - 2400000.5``, in the
requested ``UTC``, ``TAI``, ``TT``, ``TDB``, ``UT1`` or ``A1`` scale. A Julian
day contains 86400 SI seconds for these numerical conversions. A1 is GMAT's
internal atomic time scale. GMAT's raw ``*ModJulian``/``*MJD`` APIs use a
different numerical origin, ``JD - 2430000.0``; the difference is 29999.5 days.
Do not pass conventional MJD directly into an arbitrary native MJD field.

Frames and complete six-states
------------------------------

Propagation input and :class:`gmatpy.Sample` output always use
``EarthMJ2000Eq``. A :func:`gmatpy.transform_state` call explicitly converts
both position and velocity at an epoch:

.. list-table:: Supported Earth-centered frames
   :header-rows: 1
   :widths: 24 76

   * - Token
     - Meaning
   * - ``EarthMJ2000Eq``
     - GMAT's Earth-centered mean equator and equinox of J2000 frame (FK5).
   * - ``EarthMJ2000Ec``
     - Earth-centered J2000 mean ecliptic axes.
   * - ``EarthICRF``
     - Earth-centered ICRF axes, using the bundled native rotation table for
       MJ2000Eq/ICRF conversion.
   * - ``EarthFixed``
     - GMAT's Earth-fixed ``BodyFixed`` axes using its FK5/IAU1980 convention
       and bundled Earth-orientation/nutation inputs.

These tokens are case-sensitive. ``EarthMJ2000Eq``, ``EarthICRF``, GCRS and TEME
must not be treated as interchangeable labels. ``EarthFixed`` is not advertised
as ITRF or TEME. The facade does not supply TEME, ITRS or GCRS transformations.
Use an appropriate external adapter for those contracts.

Rotating-frame velocity is the derivative of position in the destination
frame. It includes the rotation-rate contribution, rather than just rotating
the three velocity components. Transform a complete six-state when passing
data to an Earth-fixed or TEME workflow.

:func:`gmatpy.body_state` uses MJ2000Eq axes but changes the origin by subtracting
the requested origin body's state. It returns a geometric state, without
light-time or aberration correction. ``Moon`` aliases ``Luna``. The supported
body set is ``Sun``, ``Mercury``, ``Venus``, ``Earth``, ``Luna``, ``Mars``,
``Jupiter``, ``Saturn``, ``Uranus``, ``Neptune`` and ``Pluto``.

For impulses, ``EarthMJ2000Eq`` specifies inertial Cartesian delta-v components.
``VNB`` is the instantaneous local frame with the first axis along velocity,
the second along the orbit normal (position cross velocity), and the third
completing the right-handed system. VNB is not the same ordering as RTN/RSW.
Burn-time samples are post-burn; simultaneous burns execute in schedule order.

.. _state-representations:

State representations and units
-------------------------------

Cartesian six-states use ``[x, y, z, vx, vy, vz]`` in **km and km/s**. Elapsed
time and step limits use seconds. Spacecraft mass is kg, drag/SRP area is m²,
and ``cd``/``cr`` are dimensionless. Delta-v is km/s. Gravitational parameter
``mu`` is km³/s². F10.7/F10.7A are in solar flux units
(10⁻²² W m⁻² Hz⁻¹); Kp is dimensionless.

:func:`gmatpy.convert_state` exposes the following case-sensitive formats.
All angular components in these layouts are **degrees**, and eccentricities
and the indicated equinoctial components are dimensionless.

.. list-table:: Six-component representation order
   :header-rows: 1
   :widths: 27 73

   * - Format
     - Components
   * - ``Cartesian``
     - x, y, z (km); vx, vy, vz (km/s)
   * - ``Keplerian``
     - Semi-major axis (km), eccentricity, inclination, RAAN, argument of
       periapsis, anomaly
   * - ``ModifiedKeplerian``
     - Periapsis radius (km), apoapsis radius (km), inclination, RAAN, argument
       of periapsis, anomaly
   * - ``Equinoctial``
     - Semi-major axis (km), h, k, p, q, mean longitude
   * - ``ModifiedEquinoctial``
     - Semi-latus rectum (km), f, g, h, k, true longitude
   * - ``SphericalRADEC``
     - Position magnitude (km), position right ascension, position declination,
       speed (km/s), velocity right ascension, velocity declination
   * - ``SphericalAZFPA``
     - Position magnitude (km), position right ascension, position declination,
       speed (km/s), velocity azimuth, vertical flight-path angle

For Keplerian/ModifiedKeplerian conversion, ``anomaly`` selects ``TA`` (true,
the default), ``MA`` (mean), ``EA`` (eccentric) or ``HA`` (hyperbolic).
Select a compatible conic and use the same anomaly convention on conversion
back. These are osculating representations, not fitted mean/TLE elements.

For the equinoctial definitions below, let :math:`e` be eccentricity,
:math:`i` inclination, :math:`\Omega` RAAN and :math:`\omega` argument of
periapsis. GMAT uses:

* ``Equinoctial``: :math:`h=e\sin(\Omega+\omega)`,
  :math:`k=e\cos(\Omega+\omega)`, :math:`p=\tan(i/2)\sin\Omega`,
  :math:`q=\tan(i/2)\cos\Omega`; the final component is mean longitude.
* ``ModifiedEquinoctial``: :math:`f=e\cos(\Omega+\omega)`,
  :math:`g=e\sin(\Omega+\omega)`, :math:`h=\tan(i/2)\cos\Omega`,
  :math:`k=\tan(i/2)\sin\Omega`; the final component is true longitude.

In ``SphericalAZFPA``, azimuth is measured from local north toward east.
The **vertical** flight-path angle is the angle between outward radius and
velocity, so a locally horizontal velocity has 90°, rather than 0°.

Conversion is delegated to native GMAT and retains its domain restrictions
and singularities. For example, the equinoctial implementation rejects
parabolic/hyperbolic orbits, and its inclination-180° singularity remains;
modified equinoctial conversion also has a retrograde singularity. Spherical
conversions need nonzero position and speed. A supported format token does
not guarantee that every six-number input represents a valid orbit.

Forces and sampling
-------------------

The default :class:`gmatpy.ForceModel` uses Earth EGM96 8×8 gravity, Sun and
Moon point-mass gravity, spherical solar radiation pressure, and no drag.
Earth gravity supports EGM96 through 360×360 or JGM3 through 70×70; order
cannot exceed degree. A zero degree selects Earth's monopole, with a
degree/order-zero primary gravity field retained when drag requires it.

Drag uses Jacchia-Roberts with the caller's constant daily F10.7, average
F10.7 and Kp. The defaults are 150, 150 and 3. These constants do not stand
for measured or forecast weather over a mission. Value-based spacecraft mass,
areas and coefficients stay constant; impulses do not consume mass.

Propagation uses native Prince-Dormand 7/8 integration. ``accuracy`` is the
native integrator setting, not a promised error in km or km/s. ``max_step_s``
limits integration steps; it does not determine the output cadence. Each
propagation call starts a fresh orbit. The multi-spacecraft helper shares one
force model and propagation setup, with individual spacecraft properties;
it does not model mutual forces or collisions.

Scientific inputs and date limits
---------------------------------

Installed artifacts bundle selected scientific inputs; they do not download or
refresh them at runtime. A successful call does not establish that a snapshot
is current or suitable for the requested scientific accuracy.

.. list-table:: Bundled input limits at the documented source revision
   :header-rows: 1
   :widths: 25 75

   * - Input
     - Coverage and consequences
   * - Native DE405
     - JD 2430000.5 through 2525008.5 TDB (1941-01-06 through 2201-02-20).
       Used by default Sun/Moon forces and :func:`gmatpy.body_state` in both
       profiles. Outside-range native requests can fail.
   * - Earth orientation
     - The inherited ``eopc04_08.62-now`` snapshot spans 1962-01-01 through
       2026-09-14 and includes forecast/error-sentinel rows. It is not a live
       set of final observations. Native extrapolation outside its coverage
       reduces fidelity; acceptance of an epoch does not validate that result.
   * - ICRF rotation vectors
     - ``ICRF_ERFA_Table.txt`` covers GMAT A1MJD 6935.000000397937 through
       58070.00000039794 (approximately 1960-01-01 through 2100-01-01).
       Native interpolation rejects epochs outside this table. The table was
       independently generated with ERFA 2.0.1; it is not an official SOFA
       release or an assertion of numerical identity with the inherited table.
   * - UTC offsets/leap seconds
     - ``tai-utc.dat`` includes historical drift segments and leap-second
       entries through the change effective 2017-01-01. No automatic updates
       are performed. Future civil-time conversions depend on this snapshot.

The limits apply to the operations and forces that use each input, not as one
uniform validated epoch range for the entire API. Inspect the bundled
``gmatpy/licenses/DATA_MANIFEST.json`` for source URLs, hashes, regeneration
notes and scientific changes. Both profiles retain the inputs required for
the propagation/time/frame/DE405 facade. Extended additionally includes native
SPICE kernel facilities; this does not extend every convenience API contract.

AGI/CSSI space-weather files, Schatten forecasts and the unused ``marini.dat``
are excluded from wheel/source distributions. Native callers selecting
file-based weather must supply appropriate inputs through
``CSSISpaceWeatherFile``/``SchattenFile``. Missing selected inputs raise an
exception; there is no automatic substitute forecast. The legacy SVN data
updater is excluded.

The tests exercise analytic cases, regression cases and selected native
comparisons. They do not establish complete GMAT coverage, numerical
equivalence to NASA releases, or qualification for operational mission analysis.
