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

   Public ``gmatpy`` 0.2.1 is on PyPI with standard-GIL CPython 3.12 through
   3.15 wheels for Linux x86_64/ARM64 and macOS Intel/ARM64. Every final wheel
   passed native installed tests before and after publication. The single
   headless package includes SPICE and all supported mission workflows;
   no feature profile or extra is needed. The separately qualified Windows x64
   addition is described in :doc:`windows`. See :doc:`installation`.


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

The original Linux/macOS 0.2.1 wheels use packaging source ``6b5c286c`` and byte-identical native
binaries from ``f8d8e4ce``. All sixteen final wheels passed 209 tests plus
three subtests before publication and again through fresh native PyPI
installation checks. Public 0.2.0 retains its original ``09eafabe`` packaging
and ``b52941e`` native provenance. See :ref:`platform-support` for exact
receipts, tested patches/hosts and remaining platform limits.

.. toctree::
   :maxdepth: 2
   :caption: Use GMAT Py
   :hidden:

   installation
   windows
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
