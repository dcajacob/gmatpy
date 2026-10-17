.. _installation:

Installation
============

Public ``gmatpy`` 0.2.0 is available on
`PyPI <https://pypi.org/project/gmatpy/0.2.0/>`_ with standard-ABI CPython 3.14
wheels for Linux x86_64/ARM64 and macOS Intel/ARM64, plus a source archive for
deliberate native builds. This checkout prepares the unreleased |release|
compatibility candidate. Candidate files must not replace immutable 0.2.0 files.

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

   python3.14 -m venv .venv
   . .venv/bin/activate
   python -m pip install --only-binary=:all: gmatpy==0.2.0
   python -c "import gmatpy; print(gmatpy.__version__); print(gmatpy.capabilities())"

For a verified local candidate, use its actual matching wheel path instead.
Binary-only installation avoids accidental source fallback. With uv::

   uv python pin 3.14
   uv add --no-build-package gmatpy gmatpy==0.2.0

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

The package metadata permits source-build attempts on Python 3.10 and later.
The qualified wheels use the standard CPython 3.14 ABI; other Python versions,
interpreters, free-threaded Python and Windows remain unqualified. Earlier
Windows results remain historical. A CMake-gated Windows x64 development path
exists; Windows ARM64 is outside that path. Earlier results for other source
revisions do not qualify a changed source tree or scientific defaults.

Linux ARM64 builds rebuild CSPICE C sources natively using the project's LP64
port configuration. This is not an official NAIF ARM64 toolkit distribution.
Wheel tags and successful installation alone do not establish numerical or
runtime qualification on an untested platform. The release must retain the
source and final artifact identities for every platform it offers.

Unreleased expansion candidate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The new matrix pins the latest stable patches when prepared: CPython 3.12.15,
3.13.16 and 3.14.8 on each of the four targets above. After all twelve core
cells pass, a four-cell 3.15.0 assessment runs. Each builds an ABI-specific wheel
from one shared immutable source archive, clean-installs it, then checks
propagation, saved states, splines/MSISE, native dependencies, notices and all
17 scientific inputs and exclusions. A configured cell is not a successful or
published wheel. Final support requires its exact retained file and receipt.
Windows, free-threaded Python and other interpreters remain unqualified.

Pinned standalone interpreters supply current security patches absent from
some runner catalogs. Archive hashes, actual runtime patches and standard ABI
are checked before use. They are build tools, not extra wheel payload.

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
