Propagate your first orbit
============================

Install a matching wheel using :doc:`installation`. Both profiles support
this example; the installed runtime needs only the standard library and its
bundled binaries/data.

.. literalinclude:: examples/quickstart.py
   :language: python
   :caption: examples/quickstart.py

The initial six-state is ``[x, y, z, vx, vy, vz]`` in **km** and **km/s**, in
EarthMJ2000Eq (Earth-centered mean equator/equinox J2000). The example starts
at an explicitly UTC epoch and samples elapsed SI seconds. The return value
is a list of immutable :class:`~gmatpy.Sample` values; ``state`` concatenates
the position and velocity tuples.

``times=[0, 300, 600]`` asks for samples at those offsets from the epoch. It does
not request successive steps of 0, 300, and 600 seconds. Repeated offsets repeat
the same state, and an empty sequence produces an empty result. Each call starts
a new orbit; a second call does not continue the first call's internal state.
Negative, non-finite, or decreasing sample times are rejected.

Choose a force model
----------------------

The default :class:`~gmatpy.ForceModel` uses EGM96 8×8 Earth gravity, Sun and
Moon point masses, and spherical solar radiation pressure (SRP). Drag is off.
The integrator is adaptive Prince-Dormand 7/8, with ``accuracy=1e-12`` and
``max_step_s=60.0``. Accuracy is an integrator setting, not a bound on physical
orbit prediction error. Output spacing and maximum integration step are
separate choices.

For a two-body comparison:

.. code-block:: python

   two_body = gmat.ForceModel(degree=0, sun=False, moon=False, srp=False)
   samples = gmat.propagate(
       [7000, 0, 0, 0, 7.5, 1.0], "2020-07-20T12:00:00Z", [0, 600],
       forces=two_body,
   )

For degree/order 70 Earth gravity and constant-flux Jacchia-Roberts drag:

.. code-block:: python

   forces = gmat.ForceModel(degree=70, order=70, drag=True,
                           f107=150.0, f107a=150.0, kp=3.0)
   spacecraft = gmat.Spacecraft(mass_kg=1000, drag_area_m2=5, srp_area_m2=5)
   samples = gmat.propagate(
       [7000, 0, 0, 0, 7.5, 1.0], "2020-07-20T12:00:00Z", range(0, 3601, 60),
       forces=forces, spacecraft=spacecraft,
   )

EGM96 supports degree/order through 360; JGM3 supports through 70. The
spacecraft has constant mass, areas, Cd and Cr. File-driven space weather is
not used by this helper. See :doc:`conventions` for model/data limits and
:doc:`examples` for runnable utility and mission examples.

Use copied values outside native calls
----------------------------------------

Value-based helpers return Python numbers, tuples, lists, or dictionaries that
you can safely retain. GMAT itself has process-global state: calls are serialized,
and parallel jobs must use spawned processes. Do not load a second GMAT API in
the same process. :func:`~gmatpy.native_session` has stricter native object
lifetime rules, explained in :doc:`workflows`.
