Runnable examples
===================

These examples use only the Python standard library and an installed ``gmatpy``
wheel. Download each Python file and run it with that wheel's interpreter::

    python quickstart.py

Run all six from a source checkout after installing a matching wheel::

    python docs/run_examples.py

The runner starts each example with isolated Python (``-I``), a fresh process,
and a temporary working directory. It does not build or install the package.
Each example includes assertions of API behavior or scientific invariants.
These checks are limited numerical regressions, not operational qualification
or a claim of equivalence with a NASA GMAT installation.

Quickstart: circular orbit
----------------------------

Available in both profiles. Explicit point-mass settings make the circular-orbit
position check independent of the default perturbations. Change the force model
deliberately when moving to a perturbed orbit; circular geometry will then no
longer be the appropriate invariant.

:download:`Download quickstart.py <examples/quickstart.py>`

.. literalinclude:: examples/quickstart.py
   :language: python

Time, frames, elements, and ephemeris
---------------------------------------

Available in both profiles. This combines a conventional MJD check, osculating
Keplerian elements, a complete position/velocity frame conversion, and the
geometric Earth–Moon state. ``EarthFixed`` uses GMAT's FK5/IAU1980 convention;
it is not advertised as ITRF or TEME. The offsets checked below apply to the
specific July 2020 epoch.

:download:`Download utilities.py <examples/utilities.py>`

.. literalinclude:: examples/utilities.py
   :language: python

Impulses and two spacecraft
-----------------------------

Requires the extended profile. A 10 m/s impulse in the velocity direction affects
only the selected spacecraft. Samples at the burn epoch are post-burn, and
duplicate output times return identical values. Impulses do not consume mass.
The single-spacecraft and multi-spacecraft helpers are checked against each
other. On minimal, this example verifies the early capability error and prints
``SKIP``.

:download:`Download impulses.py <examples/impulses.py>`

.. literalinclude:: examples/impulses.py
   :language: python

Target an instantaneous SMA change
------------------------------------

Requires the extended profile. ``target_sma`` uses the native differential
corrector to solve a tangential VNB burn at the input epoch. It supports
Earth-centered elliptic starting orbits; the requested post-burn SMA is not a
transfer trajectory or time-of-flight constraint. This circular starting orbit
also permits an independent vis-viva check of the solved delta-v.

:download:`Download target_sma.py <examples/target_sma.py>`

.. literalinclude:: examples/target_sma.py
   :language: python

Trusted script: finite burn
-----------------------------

Requires the extended profile. Download both files into the same directory.
The Python driver reads the script beside itself and replaces the gravity-file
placeholder with the installed wheel's data path in a temporary script. Run
``trusted_script.py`` to execute a 1 N, 10 s chemical-thruster burn with propellant
depletion, then compare its mass flow and velocity change with independent
calculations. No optional propulsion plugin is required for this core script.

``run_script`` executes trusted GMAT commands with the process's permissions.
Scripts may write files and run command loops; they are not sandboxed. Its
``outputs`` mapping requests runtime fields and receives copied strings. A
script using unavailable plugins or arbitrary other GMAT facilities is outside
this example's coverage.

:download:`Download trusted_script.py <examples/trusted_script.py>` and
:download:`finite_burn.script <examples/finite_burn.script>`.

.. literalinclude:: examples/trusted_script.py
   :language: python

.. rubric:: Accompanying GMAT script

.. literalinclude:: examples/finite_burn.script
   :language: text

Scoped native API and error recovery
--------------------------------------

Available in both profiles. Native handles belong to their ``native_session``
and must never be used afterward. Copy ordinary Python values before leaving
the context. Convenience calls that enter the engine and another native session
cannot be nested inside an active session. Cleanup still runs when a native
exception escapes.

The session exposes bundled SWIG bindings with their native ownership rules;
constructing a simple spacecraft does not establish coverage for the full GMAT
API or omitted plugins.

:download:`Download native_session.py <examples/native_session.py>`

.. literalinclude:: examples/native_session.py
   :language: python
