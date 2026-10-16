.. _development:

Development and validation
==========================

The Python package is built around GMAT R2026a's native C++ engine and SWIG
bindings. The convenient Python interface is in ``python/gmatpy/``; its package
build configuration is in ``pyproject.toml`` and ``python/CMakeLists.txt``.
``python/tests/`` exercises the installed interface, and ``python/tools/`` and
``python/ci/`` contain artifact and platform qualification tools.

Use an isolated checkout and environment. Native builds take substantially more
work than documentation builds; :ref:`source-build` describes their compilers,
CSPICE dependency and platform flags. The wheel build disables the GUI, optional
plugins, CSALT, legacy data updater and Java API. Building the upstream desktop
application is a separate workflow.

.. _documentation-build:

Build the documentation
-----------------------

Documentation tooling requires Python 3.11 or later; the checked configuration
uses CPython 3.14. From the repository root, create an environment and install
only the pinned documentation requirements:

.. code-block:: console

   python3.14 -m venv .venv-docs
   . .venv-docs/bin/activate
   python -m pip install -r docs/requirements.txt
   python docs/check_api.py
   python -m sphinx -W --keep-going -n -b html docs docs/_build/html

Open ``docs/_build/html/index.html`` in a browser. The Sphinx configuration reads
the Python source to check documented public signatures; it does not import or
compile the native engine. A documentation-only contributor and Read the Docs
therefore need neither CSPICE nor a GMAT wheel.

Check external documentation links separately:

.. code-block:: console

   python -m sphinx -W --keep-going -b linkcheck docs docs/_build/linkcheck

Link checking needs network access. A failed request can reflect a moved URL,
server rate limiting or unavailable network access; inspect the report instead
of treating it as a numerical-test result.

Run the executable examples in an environment with an actual matching GMAT Py
wheel installed:

.. code-block:: console

   python -m pip install /absolute/path/to/gmatpy-0.2.0-<python>-<abi>-<platform>.whl
   python docs/run_examples.py

Use the actual wheel filename and its matching interpreter. The example runner
is separate from the source-only Sphinx build so rendered documentation does not
silently substitute mocked numerical results. Run all six examples against
the standard package when changing the documented workflows.

The ``.readthedocs.yaml`` configuration describes a documentation-only build. It
does not publish a wheel or qualify a native platform. The hosted documentation
is live at https://gmatpy.readthedocs.io/en/latest/; publication of a wheel remains
a separate release action.

The configuration follows the official
`Read the Docs v2 reference <https://docs.readthedocs.com/platform/stable/config-file/v2.html>`_.
It selects Ubuntu 24.04, Python 3.14, the pinned requirements and
``sphinx.fail_on_warning``. The source reference uses Sphinx's
`Python domain <https://www.sphinx-doc.org/en/master/usage/domains/python.html>`_
instead of importing native modules during a build. ``check_api.py`` verifies
all exported names, object kinds, argument order/kinds and default values.
It does not validate prose or numerical behavior; review and installed-wheel
examples remain necessary. The documentation workflow runs this check and
the strict HTML build without compiling GMAT or publishing artifacts.

.. _native-validation:

Test an installed wheel
-----------------------

Use a clean environment, install the exact wheel, and run tests from a directory
outside the checkout. Keep any unrelated GMAT installation and its library paths
out of that environment:

.. code-block:: console

   python3.14 -m venv /absolute/path/to/new-test-env
   /absolute/path/to/new-test-env/bin/python -m pip install /absolute/path/to/selected.whl pytest
   mkdir -p /absolute/path/to/outside-source
   cd /absolute/path/to/outside-source
   /absolute/path/to/new-test-env/bin/python -m pytest -q -ra /absolute/path/to/gmatpy/python/tests

Select the interpreter and standard wheel for the platform under test.
Review skip reasons as well as the pass count; a skip is not evidence that the
associated calculation ran. The full qualification driver additionally
verifies every installed package byte against the wheel, including native
libraries, so a source-path overlay cannot be mistaken for an installed test.

Native qualification for base revision
``bff0ed4687964cd1f36a3ebaeb278b451bac271d`` passed all eight historical
profile/target cells across Linux x86_64/ARM64 and macOS Intel/ARM64 on the
first attempt. The single-package cleanup does not change scientific code or inputs,
but task-local checks using retained extended binaries remain checks against
those identified binaries, not fresh native builds from the changed source.
See :ref:`platform-support` for the exact evidence boundary.

.. list-table:: What the tests establish
   :header-rows: 1
   :widths: 28 72

   * - Checks
     - Evidence and boundary
   * - Analytic numerical cases
     - Two-body circular propagation and Keplerian conversions compare with
       independent equations. Finite-burn tests check thrust and mass flow for
       the tested script configuration.
   * - Native API comparison
     - A published GMAT example is constructed through the bundled native API
       and compared with the convenience interface. This checks setup and
       translation using the same engine.
   * - Interface and lifetime tests
     - Validation, time-scale offsets, frame round trips and rotating velocity,
       body-state origins, capability reporting, mission semantics, script errors,
       native object cleanup, threads, spawned processes and fork rejection.
   * - Controlled NASA-source fixture
     - ``sample_states.py`` and ``check_states.py`` compare selected propagation
       and frame states with ``reference-states.json``. It was sampled from
       NASA revision ``9363e129be366520c6edb0b4079204ed60666007`` with declared
       build/startup/binding adapters and exact common inputs. Position and
       velocity limits remain ``2e-7`` km and ``2e-10`` km/s.
   * - Saved independent spline oracle
     - ``verify_splines.py`` compiles a harness against the installed
       ``GmatUtil`` library and freshly compares 320 cases / 9,920 values with
       previously saved SciPy expectations at scaled tolerance ``1e-10``.
       SciPy expectations are not regenerated in this run or in CI.
   * - Fresh analytic spline checks
     - Separate CubicSpline exact-knot, linear and rational natural-spline
       cases run against installed ``GmatUtil``. ``verify_msise.py`` compiles
       a small caller against installed ``GmatBase`` and checks exact-line and
       exact-cubic invariants. These checks require no runtime SciPy.

The historical profile runs reported zero sampled position/velocity error
against the source-controlled NASA-source fixture. The fixture embeds source,
input, sampling-script and native-library receipts. It is a bounded regression subset;
the old ERFA-based derivative reference remains separately preserved in
``reference-states-erfa-historical.json``.

The retained earlier controlled comparison recorded zero state, matrix and
epoch differences in eight historical minimal cases and ten extended cases;
minimal explicitly omitted two SPICE-only cases. Those profile runs also passed
the stricter verifiers' 17 fresh Cubic analytic cases / 54 values and 12 MSISE
analytic cases / 51 values. Their fresh comparison against the 320 saved SciPy cases had maximum
scaled error ``4.694258908022594e-13``. These are executed-input results, not
range-wide numerical bounds or newly generated SciPy references.

These checks cover specific calculations, regressions and packaging contracts.
They do not demonstrate complete GMAT functionality, independent numerical
equivalence to an unmodified NASA distribution, independent physical truth or
operational mission-analysis validation. Read the test source and its tolerances
when assessing suitability for a new use case. ``python/ci/CORE_BASELINE.md``
records the retained native changes and scientific-default dispositions.

Inspect distribution and binary contents
----------------------------------------

Run the checker for the artifact's actual platform, in a matching native tool
environment:

.. code-block:: console

   python python/tools/check_distribution.py /absolute/path/to/gmatpy-0.2.0.tar.gz
   python python/tools/check_wheel.py /absolute/path/to/linux-wheel.whl
   python python/tools/check_macos_wheel.py /absolute/path/to/macos-wheel.whl --arch arm64

Use ``--arch x86_64`` for the Intel macOS wheel. ``check_wheel.py`` uses Linux ELF
tools (``readelf``, ``nm`` and ``ldd``) to inspect dependency resolution, relative
runtime library paths and excluded GUI/Xerces/updater implementation.
``check_macos_wheel.py`` uses ``lipo``, ``otool`` and ``nm`` to inspect architecture,
minimum-OS load commands, install IDs and relocation. Inspecting a deployment
target is not a test run on that operating-system version.

``check_windows_wheel.py`` is a separate experimental x64 PE checker requiring
an existing MSVC ``dumpbin`` environment. The CMake Windows path additionally
requires ``GMAT_PY_EXPERIMENTAL_WINDOWS=ON``, x64 MSVC and target-native
``lib/cspice.lib``. Historical Windows checks are not qualification of the
current candidate; see :ref:`platform-support`.

Artifact checking verifies inventories, notices, data hashes and exclusions.
The optional ``--source-manifest`` argument binds copied package inputs to a
recorded source inventory. ``check_distribution.py --release`` also checks
unresolved release-review items. Dan CaJacob personally adopted the recorded
publication-based determination for the reviewed full headless package on
2026-10-16. Qualification requires a successful release preflight; it no longer
accepts the former CSPICE owner hold. The version scope, owner attestations,
primary sources and limits are in
``python/gmatpy/licenses/EXPORT_DETERMINATION.md`` and its JSON record.
Passing numerical or binary tests does not make an export determination.
See ``python/gmatpy/LICENSES.md`` and the component manifests for details.

Reproduce native qualification
------------------------------

The manually dispatched ``.github/workflows/native-qualification.yml`` is
configured to build one standard wheel from an immutable source archive on
Linux x86_64/ARM64 and native macOS x86_64/ARM64. Configuration is not evidence
that changed source has passed on every target. It pins Linux container digests and
macOS runner architecture. ``python/ci/requirements.txt`` pins the Python build,
repair and test tools. The driver requires standard-ABI CPython 3.14 and records
its exact patch version rather than assuming identical interpreters everywhere.

``freeze_clean_checkout.py`` rejects a dirty checkout, checks committed file
bytes, and creates a verified source archive outside the checkout. It writes a
source receipt with the revision, tree and archive hashes. For example, with
``<full-commit>`` replaced by the intended immutable revision and new output
paths:

.. code-block:: console

   python python/ci/freeze_clean_checkout.py --repo /absolute/path/to/gmatpy \
     --revision <full-commit> --output /absolute/path/to/new-frozen-output
   python python/ci/qualify.py --target linux-x86_64 \
     --sdist /absolute/path/to/new-frozen-output/artifacts/gmatpy-0.2.0.tar.gz \
     --output /absolute/path/to/new-qualification-output

Run the driver on the corresponding native host/container. Its output directory
must not exist. It rebuilds CSPICE unless ``--cspice`` supplies a matching tree
with its required ``BUILD_DEPENDENCY.json`` record; ``--archive`` can provide the
pinned NAIF source archive for that rebuild. It then builds and repairs the
standard wheel, checks artifacts and installed bytes, runs tests and numerical
comparisons, and records results and evidence hashes. Linux repair explicitly
requests ``manylinux_2_28``; macOS uses delocate and one native architecture.

The records identify tested source and artifact bytes. Setting
``SOURCE_DATE_EPOCH`` makes archive timestamps repeatable; the project does not
claim bit-identical native builds across compilers. The workflow records evidence
in job logs and has no binary upload or package-publication step. See
``python/ci/README.md`` for the retained comparison definitions and current
qualification mechanics.
