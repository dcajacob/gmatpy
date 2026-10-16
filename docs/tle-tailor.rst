.. _tle-tailor:

TLE Tailor integration
======================

`TLE Tailor <https://github.com/dcajacob/tle-tailor>`_ can use GMAT Py to
propagate a Cartesian orbit, transform its samples to TEME, and pass them to
its existing TLE fitters. GMAT Py supplies the numerical propagation and
native frame conversion. TLE Tailor, Astropy, and the fitter supply the
additional bridge and fitting workflow.

.. note::

   This integration contract was checked on 2026-10-16 against the local TLE
   Tailor adapter at ``tle_tailor/propagation/gmatpy.py`` and its tests. Those
   files are uncommitted additions in the inspected external checkout; they
   are not part of the GMAT Py source distribution or an identified released
   TLE Tailor revision. Obtain a TLE Tailor checkout containing that adapter
   before using the examples on this page. Its current packaging requests
   Python 3.14 and ``gmatpy>=0.2,<0.3`` through its ``gmat`` extra.

What the bridge requires
------------------------

The adapter calls ``gmatpy.propagate`` and ``gmatpy.transform_state``. The
standard GMAT Py package provides those operations, native DE405 inputs, and
the ICRF orientation table. Its native physics tests also use ``native_session`` to read Earth's GMAT gravitational
constant. The adapter does not require GMAT's TLE/ephemeris-propagator
plugins, SPICE kernel readers, the GUI, a separate GMAT installation,
Space-Track credentials, or live scientific-data downloads.

Install a matching GMAT Py wheel explicitly using the installation guide,
then install the adapter-bearing TLE Tailor checkout in the same isolated
environment. GMAT Py 0.2.0 is not currently published on PyPI. The
``gmat`` extra declares its dependency but does not supply a missing wheel;
the local TLE Tailor project uses a ``wheels/`` find-links directory with uv.
Use the actual matching wheel filename; the standard package has no feature
profile build tag. TLE Tailor has additional Python dependencies including
NumPy, pandas, Astropy, and its fitting libraries.

Keep the legacy, separately installed GMAT Python API out of this process.
The adapter checks for the standalone ``propagate`` and ``transform_state``
functions and reports an ``ImportError`` when it encounters legacy bindings.

Sample a Cartesian state
------------------------

Once the adapter and dependencies are installed:

.. code-block:: python

   import gmatpy
   from tle_tailor.propagation import propagate_gmatpy

   timestamps, ephemeris = propagate_gmatpy(
       [7000.0, 0.0, 0.0, 0.0, 5.3, 5.3],
       epoch="2020-01-01T00:00:00Z",
       times=[0.0, 120.0, 240.0],
       frame="EarthMJ2000Eq",
       forces=gmatpy.ForceModel(degree=8, order=8, drag=False),
       spacecraft=gmatpy.Spacecraft(mass_kg=1000.0, srp_area_m2=1.0),
   )

   assert ephemeris.shape == (3, 2, 3)

The direct adapter contract is:

.. list-table:: Inputs and returned values
   :header-rows: 1
   :widths: 24 76

   * - Value
     - Meaning
   * - ``state``
     - Six finite Cartesian values ``[x, y, z, vx, vy, vz]`` with nonzero position; km and km/s.
   * - ``epoch``
     - Timezone-aware ``datetime`` or ISO timestamp with a UTC offset; normalized to UTC.
   * - ``times``
     - Finite, nonnegative, nondecreasing elapsed SI seconds; duplicates are accepted.
   * - ``frame``
     - ``EarthMJ2000Eq`` (default), ``EarthICRF``, ``TEME``, or ``ITRS``. Generic ``ECI`` and ``ECEF`` labels are rejected.
   * - ``forces``, ``spacecraft``
     - Optional GMAT Py ``ForceModel`` and ``Spacecraft`` values; ``None`` selects the library defaults.
   * - ``accuracy``, ``max_step_s``
     - Positive integration controls forwarded to GMAT Py; defaults are ``1e-12`` and 60 seconds.
   * - ``timestamps``
     - UTC ``pandas.DatetimeIndex`` at the requested sample times.
   * - ``ephemeris``
     - Finite NumPy array shaped ``(N, 2, 3)`` in TEME: ``[:, 0, :]`` is position in km and ``[:, 1, :]`` is velocity in km/s.

Times are output offsets from the initial epoch, not per-step durations.
Each call starts a fresh orbit. An empty schedule returns an empty UTC index
and an array shaped ``(0, 2, 3)``. Invalid states, frame labels, or time
schedules raise ``ValueError``. A missing standalone installation raises
``ImportError``; failed propagation or invalid returned samples can raise
``RuntimeError``.

Frame and time contract
-----------------------

The adapter propagates in EarthMJ2000Eq, GMAT's Earth-centered mean
equator/equinox J2000 frame. For every output epoch it passes all six
components through GMAT's native EarthMJ2000Eq-to-EarthICRF transformation,
then represents that geocentric ICRF-aligned state in Astropy GCRS and
transforms it to TEME. GMAT's native MJ2000Eq/ICRF link applies the same
table-derived matrix to position and velocity, with a zero matrix-derivative
term. Astropy carries the velocity differential and frame-motion terms for
its own transformations. This preserves the native GMAT convention; it does
not add a time derivative of the ICRF table to the native velocity transform.

For TEME or ITRS input, Astropy first converts the full state to GCRS; GMAT
then converts EarthICRF to EarthMJ2000Eq. EarthICRF input needs only the GMAT
step. Both directions of the native MJ2000Eq/ICRF conversion are therefore
part of the bridge contract. A native state must not simply be relabelled
TEME, and a transformed position alone is insufficient. GMAT's EarthFixed
convention is not substituted for ITRS.

The current defaults restore NASA's exact ``ICRF_Table.txt`` values and
original unequal grid: 49,063 rows with gaps up to 16 days. Native ninth-order
Lagrange interpolation spans those gaps; the gaps are not rejected as missing
data. Requests outside the table's endpoint range are rejected. The former
ERFA-generated daily alternative changed both values and grid and is no longer
the packaged default. Restoring the NASA table changes sampled ICRF and TEME
outputs, so earlier bridge outputs or fit residuals obtained with the ERFA
alternative must be re-evaluated. It does not establish universal numerical
equivalence to a NASA release or independent physical truth.

The adapter disables Astropy IERS auto-download and uses installed Earth
orientation tables. The GMAT Py scientific inputs and the installed Astropy
IERS data both constrain usable epochs and frame accuracy. The restored Earth
PCK snapshot ends at 2026-06-12 for native SPICE workflows; the direct bridge
uses native DE405 and the ICRF table rather than SPICE kernel readers. Supply explicit
reference frames, units, and time scales when converting external launch
states or OPM data; the direct adapter does not infer those metadata or parse
OPM files.

Intervals that include or cross a UTC leap second are rejected. The native
integrator advances in SI seconds, while Python datetime and the existing
fitters cannot represent leap-second timestamps. Select separate fitting
arcs on either side of the transition rather than silently identifying UTC
datetime subtraction with elapsed SI seconds.

Fit and evaluate a TLE
----------------------

The returned TEME arrays match TLE Tailor's ephemeris fitter input. In a
checkout containing the inspected integration example, the full synthetic
state-to-TLE workflow is available as:

.. code-block:: console

   python -m tle_tailor.notebooks.gmat_integration.gmatpy_state_to_tle --method fd
   python -m tle_tailor.notebooks.gmat_integration.gmatpy_state_to_tle --method jax

The default example samples a 12,000-second arc every 120 seconds and fits an
equinoctial TLE. The FD and JAX methods belong to TLE Tailor. Its example
recomputes fitted position and velocity RMS vector errors with SGP4 at the
sample epochs. Evaluate those physical residuals over the intended use
interval; a returned TLE or finite weighted fitter sigma alone does not
establish an adequate fit. The synthetic example's satellite identity fields
are placeholders.

GMAT Py itself does not provide a standalone TLE parser, SGP4 propagator,
TLE fitter, or TLE exporter. This bridge accepts an initial Cartesian state
and samples one forward Earth orbit; it does not pass maneuver schedules,
estimation settings, or the mission wrappers to GMAT Py. The
external TLE Tailor project may provide other backends with different input
contracts.

The native matrix evidence belongs to the exact GMAT Py source revision and
artifacts recorded in :ref:`platform-support`. It does not qualify the external
TLE Tailor fitters or establish a fresh native build of the packaging cleanup.

Parallel calls follow :ref:`GMAT's native concurrency rules <native-access>`:
use spawned processes for independent work. Within one process, GMAT calls
serialize; the adapter additionally serializes its Astropy IERS configuration
context. Validate your own state, physical parameters, fitting interval, and
installed library versions before relying on the resulting TLE.
