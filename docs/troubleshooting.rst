Errors and troubleshooting
============================

Start with the Python exception and the operation that failed. Fix input or
installation problems before changing physical or numerical settings. The
facade validates common input errors, but it does not normalize every native
exception into one Python exception type.

.. list-table:: Common failures
   :header-rows: 1
   :widths: 27 36 37

   * - Symptom
     - Likely cause
     - Action
   * - Pip reports no matching distribution or unsupported wheel
     - The file targets a different interpreter ABI, OS, or architecture;
       or installation was attempted from PyPI.
     - Use an explicit wheel path matching the active Python. Check
       ``python --version`` and ``python -m pip debug --verbose``.
   * - ``UnsupportedCapabilityError``
     - A capability is missing, or an older candidate installation is being used.
     - Check :func:`~gmatpy.capabilities`. The standard package includes all
       documented mission operations; install a matching standard wheel in a
       clean environment if an older candidate is present.
   * - ``ValueError`` for epoch, state, or time
     - Naive/malformed datetime; non-finite or wrong-length state; zero position;
       negative/decreasing sample times; or an unsupported token.
     - Use a timezone-aware datetime or ISO timestamp, six finite components,
       and nonnegative nondecreasing elapsed seconds. Tokens are case-sensitive.
   * - ``TypeError`` for forces, spacecraft, impulses, or script outputs
     - A mapping/value has the wrong structure or class.
     - Use the public dataclasses and the mapping shapes in :doc:`api`.
       Script output fields must be sequences, rather than a single string.
   * - Missing scientific data or native library import failure
     - Incomplete/corrupted wheel, manual package copying, or incompatible
       runtime dependencies.
     - Reinstall a checked matching wheel in a fresh environment. Preserve
       the exact exception, wheel hash, OS, Python, and capabilities for a report.
   * - Initialization failed; an ``engine.log`` path is shown
     - The bundled engine could not initialize its startup/data configuration.
     - Inspect that private temporary log while the process is still alive.
       Startup/logs are written outside site-packages.
   * - Calls cannot be nested
     - A helper or a second native session was entered inside an active session.
     - Copy values, leave the ``with`` block, then call the helper.
   * - Call rejected after fork
     - A child inherited GMAT's process-global runtime.
     - Use ``multiprocessing.get_context("spawn")`` and initialize independently
       in each child. Threads serialize native access.
   * - Propagation/targeting failure or non-finite result
     - Native integration/solver failure, singular/unsupported physical state,
       data-range issue, or floating-point time resolution.
     - Reduce to a short reproducible case with explicit state, epoch, forces,
       steps, and target settings. Check data coverage and orbit assumptions.
   * - Script fails to load/run or an output object is missing
     - Syntax, unavailable plugin, invalid field/object name, or a mission
       command failed.
     - Use a trusted core-only script and verify field spelling and runtime
       object names. ``run_script`` clears native objects even on failure.

Handle expected failures narrowly
-----------------------------------

.. code-block:: python

   import gmatpy as gmat

   if gmat.capabilities().supports("impulsive_maneuvers"):
       result = gmat.propagate_mission(
           [7000, 0, 0, 0, 7.5, 1.0], "2020-07-20T12:00:00Z", [0, 600],
           impulses=[gmat.Impulse(60, (0.001, 0, 0))],
       )

All currently documented mission operations are included.
:exc:`~gmatpy.UnsupportedCapabilityError` remains available for compatibility
and capability-dependent code. Catch ``ValueError`` where user input can be
corrected. Native ``APIException``
may also propagate; broad exception handling should preserve the original
diagnostic and avoid pretending that a failed computation succeeded.

The :doc:`examples` include validation-error recovery. They check that a later
valid operation still works after expected errors. Native-session cleanup does
not make handles safe to retain after the context exits, and script execution
is not a sandbox: scripts can write files or loop indefinitely.

Report a reproducible issue
-----------------------------

Include the exact ``gmatpy`` version and capabilities, wheel filename and SHA-256,
Python version/ABI, OS/architecture, traceback, a small script, and any relevant
data coverage. Describe whether the result differs from an analytical reference,
an independent implementation, or another GMAT Py build. These comparisons have
different implications. Open an issue in the
`project tracker <https://github.com/dcajacob/gmatpy/issues>`_.
