.. _installation:

Installation
============

Public ``gmatpy`` 0.2.1 is available on
`PyPI <https://pypi.org/project/gmatpy/0.2.1/>`_ with standard-GIL CPython
3.12 through 3.15 wheels for Linux x86_64/ARM64 and macOS Intel/ARM64,
plus a matching source archive for deliberate native builds.

There is one standard headless package per supported Python ABI and platform.
It includes the native engine, Python bindings, SPICE support and 17 selected
scientific inputs. Propagation, conversions, impulses, multiple spacecraft,
bounded SMA targeting, trusted core scripts and scoped native access are all
included. No feature profile, build tag or Python extra is needed.

A wheel needs no separate GMAT installation, GUI, display server or runtime data
download. The Python runtime interface uses the standard library; building from
source has additional native requirements. Optional GMAT plugins and GUI
workflows are outside the package's supported interface.

Install a matching wheel
-------------------------

Use an isolated environment, particularly if you already use the separately
installed GMAT Python API, which also uses the name ``gmatpy``. Create the
environment with the interpreter matching the wheel:

.. code-block:: console

   python3.13 -m venv .venv
   . .venv/bin/activate
   python -m pip install --only-binary=:all: gmatpy==0.2.1
   python -c "import gmatpy; print(gmatpy.__version__); print(gmatpy.capabilities())"

For a verified local candidate, use its actual matching wheel path instead.
Binary-only installation avoids accidental source fallback. With uv::

   uv python pin 3.13
   uv add --no-build-package gmatpy gmatpy==0.2.1

For uv projects, set ``requires-python`` within the supported range, for
example ``>=3.13,<3.16``, and pin the interpreter you intend to run.

For example,
``cp314-cp314`` identifies the standard CPython 3.14 ABI; it is not a
free-threaded or cross-version wheel. The platform tag must also match the
machine and operating system. Pip rejects an incompatible wheel. See
:doc:`workflows` for feature boundaries and capability reporting.

Earlier candidate wheels used ``1minimal`` and ``2extended`` build tags. Those
are historical artifacts, not choices in the standard distribution. Replace an
older candidate in a clean environment using the actual new wheel filename.
Do not install a second distribution that also owns the ``gmatpy`` import tree.

.. _platform-support:

Platform qualification
----------------------

Published 0.2.1 release evidence
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The original Linux/macOS ``gmatpy==0.2.1`` release provides sixteen wheels: standard-GIL CPython
3.12.15, 3.13.16, 3.14.8 and 3.15.0 on Linux x86_64/aarch64 and macOS
Intel/ARM64. Each final wheel passed 209 tests plus three subtests, exact
installed-byte/version checks and saved-state comparisons both
`before publication <https://github.com/dcajacob/gmatpy/actions/runs/39008578034>`_ and through fresh native
`PyPI installation checks <https://github.com/dcajacob/gmatpy/actions/runs/39010062762>`_.
`Production publication <https://github.com/dcajacob/gmatpy/actions/runs/39009509178>`_ and independent public downloads verified
all seventeen unchanged files against the
`fixed release hash allowlist <https://github.com/dcajacob/gmatpy/blob/cbb8554bf52366ca2646343d906dcda14d4363f8/.github/release/pypi-0.2.1.json>`_. Public 0.2.0 files remain unchanged.

Packaging source is ``6b5c286cfbd64500a848277aeed0aee9b2e440fc``; native compilation origin stays
``f8d8e4ce997ca7400afbe035b7ec55bd66c02575``. All 48 native library instances
and sixteen SWIG wrappers were reused byte-for-byte, with separate original
qualification/interpreter/CSPICE receipts and binary-reuse provenance.
The original native numerical-oracle checks are carried forward for identical
bytes; the final installed-wheel checks above are new runs. No native rebuild
or repair was performed for those sixteen Linux/macOS files. The Windows
addition uses a separate fresh native build; see :doc:`windows`.

Windows x64 is separately qualified in :doc:`windows`. Windows ARM64,
free-threaded Python and other interpreters remain unqualified.
Wheel deployment tags do not prove runtime execution on every older OS or
historical interpreter patch. Scientific input coverage/freshness limitations
remain documented in :doc:`conventions`.

Historical 0.2.0 qualification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Qualification on 2026-10-16 for source
``b52941e9830940c3086839431fd1fb64812076ff`` built the single full headless wheel
for each target below, with 194 tests passed and no skips per target. Linux
x86_64 was qualified locally; the other three targets passed
`native run 38970516533 <https://github.com/dcajacob/gmatpy/actions/runs/38970516533>`_.
These results identify that exact revision; successor artifacts require their
own source/build receipts and validation. The eight profile/target cells for
the earlier ``bff0ed4687964cd1f36a3ebaeb278b451bac271d`` revision remain
historical evidence with their original source and profile identities.

.. list-table:: Qualified CPython 3.14 wheels for b52941e
   :header-rows: 1
   :widths: 22 24 54

   * - Operating system
     - Architecture
     - Qualification scope
   * - Linux
     - x86_64
     - Standard-ABI CPython 3.14.7 on glibc 2.28. Dual manylinux 2.24/2.28 tags
       were audited; glibc 2.24 through 2.27 execution was not tested.
   * - Linux
     - ARM64/aarch64
     - Standard-ABI CPython 3.14.8 on glibc 2.28. Dual manylinux 2.24/2.28 tags
       were audited; glibc 2.24 through 2.27 execution was not tested.
   * - macOS
     - Apple Silicon arm64
     - Standard-ABI CPython 3.14.7 on macOS 15.7.9. The 11.0 deployment tag
       does not establish runtime execution on macOS 11 through 14.
   * - macOS
     - Intel x86_64
     - Standard-ABI CPython 3.14.7 on macOS 15.7.9. The 11.0 deployment tag
       does not establish runtime execution on macOS 11 through 14.

Public 0.2.0 metadata permits source-build attempts on Python 3.10 and later.
Those public wheels use the standard CPython 3.14 ABI; other Python versions,
interpreters, free-threaded Python and Windows remain unqualified. Earlier
Windows results remain historical. A CMake-gated Windows x64 development path
exists; Windows ARM64 is outside that path. Earlier results for other source
revisions do not qualify a changed source tree or scientific defaults.

Linux ARM64 builds rebuild CSPICE C sources natively using the project's LP64
port configuration. This is not an official NAIF ARM64 toolkit distribution.
Wheel tags and successful installation alone do not establish numerical or
runtime qualification on an untested platform. The release must retain the
source and final artifact identities for every platform it offers.

Original native expansion candidate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The immutable ``0.2.1.dev0`` candidate from source ``f8d8e4ce997ca7400afbe035b7ec55bd66c02575``
passed all twelve core ABI/target cells below, followed by all four
standard-ABI CPython 3.15.0 assessment cells. Each exact wheel passed
209 tests plus three subtests, clean installed-byte checks, native dependency
and data/notices audits, saved-state comparisons and spline/MSISE regressions.
These candidate files have not been published to PyPI. Public 0.2.0 still has
only the CPython 3.14 wheels described above.

.. list-table:: Candidate f8d8e4ce qualification
   :header-rows: 1
   :widths: 20 20 20 20 20

   * - CPython patch
     - Linux x86_64
     - Linux ARM64
     - macOS ARM64
     - macOS Intel
   * - 3.12.15
     - Passed
     - Passed
     - Passed
     - Passed
   * - 3.13.16
     - Passed
     - Passed
     - Passed
     - Passed
   * - 3.14.8
     - Passed
     - Passed
     - Passed
     - Passed
   * - 3.15.0 assessment
     - Passed
     - Passed
     - Passed
     - Passed

The `initial run <https://github.com/dcajacob/gmatpy/actions/runs/38998592411>`_ qualified both Linux 3.13 cells.
An early macOS standalone-Python CA-path failure was repaired without disabling
TLS checks. The `bounded recovery run <https://github.com/dcajacob/gmatpy/actions/runs/38999648051>`_ verified the
original source and both previous successes, then qualified the remaining
fourteen wheels from that same source archive. The workflow-only recovery
revision is ``54378760``; it is distinct from the candidate source revision.

Pinned standalone interpreters supply the exact patches above. Interpreter
archive hashes, runtime versions and standard ABI are checked before use;
the interpreters are build tools, not extra wheel payload. Linux tests ran on
glibc 2.28 and macOS tests on native macOS 15 runners. Older minimum-OS wheel
tags do not establish execution on every older host. Windows was outside that
f8 candidate; its later qualification is in :doc:`windows`. Free-threaded
Python and other interpreters remain unqualified.

The source archive and an independently rebuilt Linux x86 CPython 3.13 wheel
matched their hosted counterparts byte-for-byte. That wheel required the same
interpreter-header prefix; this is a scoped reproduction result, not a promise
of identical native output across different compilers or runner images.
See :doc:`development` for the source/artifact identities and reproduction limits.

.. _source-build:

Build a wheel from source
-------------------------

Source builds require a C compiler, a C++17 compiler, CMake 3.19 or later, a native
build tool such as Make or Ninja, and CPython development headers. Python build
requirements are ``scikit-build-core>=1.0`` and ``swig>=4.2,<5``; the ``build``
frontend is also used below. The pinned qualification tool set is in
``python/ci/requirements.txt``.

Provide a target-native CSPICE dependency tree containing ``include/SpiceUsr.h``,
``include/f2c.h`` and ``lib/cspice.a`` on Linux/macOS. Its objects must be built
with position-independent code (``-fPIC``). A precompiled archive for another
architecture cannot be reused.

Source installation does not automatically retrieve or compile CSPICE/f2c.
The sdist includes the pinned bootstrap helper, not its headers or archive.
MATLAB is not required. The candidate preflight reports missing native inputs
before legacy configuration can produce secondary linker errors. ``F2C_DIR``
is the separate f2c header directory when needed; runtime objects are in CSPICE.

Start from the intended source revision in a fresh checkout. Replace
``RELEASE_COMMIT`` with its immutable commit identifier; a task-local candidate
must be obtained from its identified checkout or archive until it is public:

.. code-block:: console

   git clone https://github.com/dcajacob/gmatpy.git
   cd gmatpy
   git checkout RELEASE_COMMIT
   python3.14 -m venv .venv
   . .venv/bin/activate
   python -m pip install -r python/ci/requirements.txt

Install the native compiler, CMake and build tool through your operating system's
development environment. Obtain the `NAIF CSPICE toolkit
<https://naif.jpl.nasa.gov/naif/toolkit.html>`_ and rebuild it for your target with
PIC enabled, or provide an already verified matching dependency tree. For the
four configured qualification targets, ``python/ci/build_cspice.py`` rebuilds the
pinned official C sources, records hashes and runs ABI probes. It downloads the
archive unless ``--archive`` supplies the pinned file. For example, on native
Linux x86_64, with a new output directory:

.. code-block:: console

   python python/ci/build_cspice.py --target linux-x86_64 --output /absolute/path/to/new-cspice

Use ``linux-arm64``, ``macos-x86_64`` or ``macos-arm64`` only on the corresponding
native target. This is a full native dependency build, not part of a normal
wheel installation or documentation build.

Pass the prepared native tree to a source build frontend::

   uv pip install . -Ccmake.define.CSPICE_DIR=/absolute/path/to/cspice

The candidate also accepts ``CSPICE_DIR`` in the environment; explicit CMake
configuration takes precedence. Public 0.2.0 raw builds need the explicit
configuration above; its Bash helper translates the environment variable.

Linux
~~~~~

The Bash helper builds the standard wheel, repairs it with auditwheel, and
checks it:

.. code-block:: console

   CSPICE_DIR=/absolute/path/to/cspice bash python/tools/build_wheel.sh

``GMAT_PY_PYTHON`` selects the build interpreter, ``GMAT_PY_WHEEL_DIR`` the
output directory, and ``CMAKE_BUILD_PARALLEL_LEVEL`` the parallelism (default 2).
The helper uses fresh intermediate directories; failures retain them for
diagnosis. ``GMAT_PY_BUILD_DIR`` can select a persistent native build directory;
keep it isolated to one target and interpreter.

For a local, host-specific wheel, add ``GMAT_PY_REPAIR=0``. This checks the wheel
but does not claim manylinux compatibility. A portable wheel must be built
against its intended baseline: auditwheel repair cannot lower the glibc version
required by binaries compiled on a newer host. The qualification workflow
explicitly builds and repairs for ``manylinux_2_28``.

macOS
~~~~~

The Linux helper is not the macOS build path. Use the native build frontend with
the experimental CMake gate and one explicit architecture. This example builds
the standard package for Apple Silicon:

.. code-block:: console

   MACOSX_DEPLOYMENT_TARGET=11.0 ARCHFLAGS="-arch arm64" \
   python -m build --wheel --no-isolation --outdir dist/macos-arm64 \
     -Cbuild-dir=build/gmatpy/macos-arm64 \
     -Ccmake.define.CSPICE_DIR=/absolute/path/to/cspice \
     -Ccmake.define.GMAT_PY_EXPERIMENTAL_MACOS=ON \
     -Ccmake.define.CMAKE_OSX_ARCHITECTURES=arm64 \
     -Ccmake.define.CMAKE_OSX_DEPLOYMENT_TARGET=11.0
   delocate-wheel --require-archs arm64 -w wheelhouse dist/macos-arm64/*.whl

For a native Intel build, change the architecture and architecture-specific paths
to ``x86_64``. Universal2 and cross-compiled builds are not covered. Do not share
native build directories or CSPICE libraries between architectures.

Validate and test the resulting installed wheel as described in
:doc:`development`, then continue with :doc:`quickstart`.
