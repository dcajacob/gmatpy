GMAT Py
=======

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

   The distribution is ``gmatpy`` version |release|, imported as ``gmatpy``.
   It is **not yet on PyPI**. Install an explicitly selected candidate wheel or
   build from source. The minimal and extended profiles share the same name and
   import tree. See :doc:`installation` before choosing an artifact.

Find your starting point
------------------------

* :doc:`installation`: choose a wheel, understand platform qualification, or
  prepare a native source build.
* :doc:`quickstart`: propagate an Earth-centered state and interpret the samples.
* :doc:`workflows`: choose a profile and explore burns, multiple spacecraft,
  targeting, scripts, and native sessions.
* :doc:`tle-tailor`: use the GMAT Py propagation backend in a TLE-fitting workflow.
* :doc:`conventions`: check time scales, reference frames, units, and data limits.
* :doc:`api`: look up every supported public Python export.
* :doc:`examples`: run the same small programs used to check this documentation.

Scope and confidence
--------------------

The value-based API covers Earth propagation, state/time/frame conversions,
geometric DE405 body states, and a bounded set of extended mission operations.
The bundled core SWIG interface is broader and experimental. Optional GMAT
plugins and GUI workflows are outside the supported facade.

Numerical tests combine analytical checks, saved independent expectations,
same-engine comparisons, and a controlled NASA-source comparison with declared
adapters. Zero differences in sampled cases do not establish universal NASA
equivalence. Their scope is described in :doc:`development`; passing them does
not validate operational mission use. Scientific inputs are fixed snapshots,
with coverage and freshness limits in :doc:`conventions`.

These pages describe core candidate
``ea39c085a95e5bf6151139bf69b977f74c80690b``. Its tested native wheels remain
bound to ``540c4c1c84bf422a96bc8667a8585beba8af2ad9``; the child changes only
verifiers, which were rerun against those exact libraries. Current native
qualification covers Linux x86_64 with standard-ABI CPython 3.14.7. Earlier
ARM64/macOS results do not qualify this changed candidate. See
:ref:`platform-support` for the exact scope and :doc:`development` for evidence
boundaries.

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
