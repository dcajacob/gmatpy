GMAT Py
=======

.. note::

   Stable 0.2.1 is being prepared locally from the qualified f8 native binaries.
   Packaging provenance and native compilation provenance are recorded
   separately; final installed-wheel validation and production approval are
   required before upload. Public 0.2.0 remains the published release.


Orbit propagation and astrodynamics in Python, backed by a bundled native
GMAT R2026a engine. Start with ordinary Python values, then use the scoped
native interface when you need lower-level control.

.. code-block:: python

   import gmatpy as gmat

   samples = gmat.propagate(
       [7000, 0, 0, 0, 7.5, 1.0],
       epoch="2020-07-20T12:00:00Z",
       times=[0, 60, 600],
   )
   print(samples[-1].position_km)

A matching wheel bundles the engine, Python bindings, and selected scientific
data. It needs no separate GMAT installation, GUI, display server, or runtime
data download. GMAT Py is an experimental, independently packaged interface;
it does not provide complete GMAT coverage or establish numerical equivalence
with a NASA GMAT release.

.. important::

   Public ``gmatpy`` 0.2.0 is on PyPI with CPython 3.14 Linux/macOS wheels.
   These pages describe the unreleased |release| compatibility candidate.
   Public files and candidate artifacts have separate source/build receipts. The single headless package includes SPICE and all supported mission
   workflows; no feature profile or extra is needed. See :doc:`installation`.

Find your starting point
------------------------

* :doc:`installation`: choose a wheel, understand platform qualification, or
  prepare a native source build.
* :doc:`quickstart`: propagate an Earth-centered state and interpret the samples.
* :doc:`workflows`: explore burns, multiple spacecraft,
  targeting, scripts, and native sessions.
* :doc:`tle-tailor`: use the GMAT Py propagation backend in a TLE-fitting workflow.
* :doc:`conventions`: check time scales, reference frames, units, and data limits.
* :doc:`api`: look up every supported public Python export.
* :doc:`examples`: run the same small programs used to check this documentation.

Scope and confidence
--------------------

The value-based API covers Earth propagation, state/time/frame conversions,
geometric DE405 body states, and a bounded set of mission operations.
The bundled core SWIG interface is broader and experimental. Optional GMAT
plugins and GUI workflows are outside the supported facade.

Numerical tests combine analytical checks, saved independent expectations,
same-engine comparisons, and a controlled NASA-source comparison with declared
adapters. Zero differences in sampled cases do not establish universal NASA
equivalence. Their scope is described in :doc:`development`; passing them does
not validate operational mission use. Scientific inputs are fixed snapshots,
with coverage and freshness limits in :doc:`conventions`.

Public 0.2.0 wheels use packaging source ``09eafabe`` and original native
binaries from ``b52941e``, which passed 194 tests per target. The public Linux
wheel also passed a fresh 194-test installed check. The separate unreleased
``f8d8e4ce`` candidate passed all four native targets on CPython 3.12.15,
3.13.16 and 3.14.8, followed by the four 3.15.0 assessment cells, with 209 tests
plus three subtests per wheel. These are candidate qualification results;
they do not add files to public 0.2.0. See :ref:`platform-support` for exact
source/build receipts, runtime hosts and remaining platform limits.

.. toctree::
   :maxdepth: 2
   :caption: Use GMAT Py
   :hidden:

   installation
   quickstart
   workflows
   tle-tailor
   conventions
   examples

.. toctree::
   :maxdepth: 2
   :caption: Reference and contribution
   :hidden:

   api
   troubleshooting
   development

Project resources
-----------------

`Source repository <https://github.com/dcajacob/gmatpy>`_ ·
`Issue tracker <https://github.com/dcajacob/gmatpy/issues>`_ ·
`NASA GMAT project <https://github.com/nasa/GMAT>`_

The wheel and source archive include component notices and license/data
inventories. Consult ``gmatpy/NOTICE.txt``, ``gmatpy/LICENSES.md``, and
``gmatpy/licenses/`` for the specific distribution. Public source availability
does not imply binary publication clearance; the product-specific CSPICE
export determination remains an owner decision.
