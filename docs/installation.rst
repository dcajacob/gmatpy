.. _installation:

Installation
============

GMAT Py is distributed as ``gmatpy``, version ``0.2.0``. It is not yet published
to PyPI. Install a matching wheel that you have obtained from the project owner,
or build a wheel from the `source repository
<https://github.com/dcajacob/gmatpy>`_. These instructions do not imply that public
binary releases are available.

A wheel contains the native engine, Python bindings and selected scientific data.
It needs no separate GMAT installation, GUI, display server or runtime data
download. The Python runtime interface uses the standard library; building from
source has additional native requirements.

Install an explicit wheel
-------------------------

Use an isolated environment, particularly if you already use the separately
installed GMAT Python API, which also uses the name ``gmatpy``. Create the
environment with the interpreter matching the wheel:

.. code-block:: console

   python3.14 -m venv .venv
   . .venv/bin/activate
   python -m pip install /absolute/path/to/gmatpy-0.2.0-<build>-<python>-<abi>-<platform>.whl
   python -c "import gmatpy; print(gmatpy.__version__); print(gmatpy.capabilities())"

Replace the entire placeholder filename with the actual wheel path. For example,
``cp314-cp314`` identifies the standard CPython 3.14 ABI; it is not a
free-threaded or cross-version wheel. The platform tag must also match the
machine and operating system. Pip rejects an incompatible wheel.

Choose minimal or extended
--------------------------

Both profiles have the same distribution name, version and ``import gmatpy``
namespace. Their wheel build tags distinguish them:

.. list-table::
   :header-rows: 1
   :widths: 16 18 66

   * - Profile
     - Build tag
     - Included interface
   * - Minimal
     - ``1minimal``
     - Propagation, state/time/frame conversion, native DE405 ephemerides and
       scoped native sessions.
   * - Extended
     - ``2extended``
     - The minimal interface plus impulsive missions, multiple spacecraft,
       bounded SMA targeting, core mission scripts and SPICE kernel support.

The source build defaults to extended. Python extras do not select a native
profile. If both files are offered to an unconstrained resolver, the wheel build
tag can favor extended; select the exact minimal file when that is your intent.
The future PyPI variant design is still pending; these build tags describe the
current explicit-wheel workflow, rather than a finalized PyPI selection policy.
To replace one profile with the other at the same version:

.. code-block:: console

   python -m pip install --force-reinstall /absolute/path/to/the-selected-profile.whl

This replaces the installed distribution. Do not install a second distribution
that also owns ``gmatpy``. See :doc:`workflows` for feature boundaries and
capability checks.

.. _platform-support:

Platform qualification
----------------------

The current source candidate is
``ea39c085a95e5bf6151139bf69b977f74c80690b``. Fresh native wheels for both
profiles were built from its parent
``540c4c1c84bf422a96bc8667a8585beba8af2ad9`` using standard-ABI CPython 3.14.7
on Linux x86_64 with glibc 2.28. The child changes only two verification tools;
those stricter tools were rerun against the exact installed wheel libraries.
The wheels retain their parent source identity and are not presented as rebuilt
from the child.

.. list-table::
   :header-rows: 1
   :widths: 22 24 54

   * - Operating system
     - Architecture
     - Qualification scope
   * - Linux
     - x86_64
     - Fresh minimal and extended qualification in a pinned
       ``manylinux_2_28`` image. The wheel baseline is glibc 2.28 or later.
   * - Linux
     - ARM64/aarch64
     - Build configuration exists; the current source has not received fresh
       native qualification on this target.
   * - macOS
     - Intel x86_64 and Apple Silicon arm64
     - Native build configurations exist; the current source has not received
       fresh qualification on either architecture.

The earlier revision ``50f61a05a1dd68ba2682d74a8631eba1b514630e`` passed a
four-target CPython 3.14 qualification across Linux x86_64/ARM64 and macOS
Intel/ARM64. Those historical results do not qualify the changed source and
scientific defaults. Its macOS runs used macOS 15 with an 11.0 deployment tag;
execution on macOS 11 through 14 was not established.

The package metadata permits Python 3.10 and later. That metadata is broader than
the current build-and-test qualification: other Python versions, free-threaded
Python and Windows are not qualified by the current candidate results. Earlier
Windows results also remain historical. A CMake-gated
Windows x64 development path exists; Windows ARM64 is outside that path.

Linux ARM64 builds rebuild CSPICE C sources natively using the project's LP64
port configuration. This is not an official NAIF ARM64 toolkit distribution.
Wheel tags and successful installation alone do not establish numerical or
runtime qualification on an untested platform.

.. _source-build:

Build a wheel from source
-------------------------

Source builds require a C compiler, a C++17 compiler, CMake 3.19 or later, a native
build tool such as Make or Ninja, and CPython development headers. Python build
requirements are ``scikit-build-core>=1.0`` and ``swig>=4.2,<5``; the ``build``
frontend is also used below. The pinned qualification tool set is in
``python/ci/requirements.txt``.

Both profiles require a target-native CSPICE dependency tree containing
``include/SpiceUsr.h``, ``include/f2c.h`` and ``lib/cspice.a`` on Linux/macOS.
Its objects must be built with position-independent code (``-fPIC``). Minimal
disables SPICE kernel facilities but still links CSPICE-supplied f2c runtime
objects used by the engine. A precompiled archive for another architecture
cannot be reused.

Start from the intended source revision in a fresh checkout:

The candidate revision below may still exist only in an owner-provided local
review checkout until source publication is approved. If the public remote
does not contain it, use that checkout or its identified source archive;
these instructions do not make a pending revision publicly available.

.. code-block:: console

   git clone https://github.com/dcajacob/gmatpy.git
   cd gmatpy
   git checkout ea39c085a95e5bf6151139bf69b977f74c80690b
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

Linux
~~~~~

The Bash helper builds, repairs with auditwheel, and checks a Linux wheel:

.. code-block:: console

   CSPICE_DIR=/absolute/path/to/cspice GMAT_PY_PROFILE=minimal bash python/tools/build_wheel.sh

Set ``GMAT_PY_PROFILE=extended`` for the other profile. ``GMAT_PY_PYTHON`` selects
the build interpreter, ``GMAT_PY_WHEEL_DIR`` the output directory, and
``CMAKE_BUILD_PARALLEL_LEVEL`` the parallelism (default 2). The helper chooses
the matching wheel build tag and uses fresh intermediate directories. Failures
retain those directories for diagnosis. ``GMAT_PY_BUILD_DIR`` can select a
persistent native build directory; keep it isolated to one profile and target.

For a local, host-specific wheel, add ``GMAT_PY_REPAIR=0``. This checks the wheel
but does not claim manylinux compatibility. A portable wheel must be built
against its intended baseline: auditwheel repair cannot lower the glibc version
required by binaries compiled on a newer host. The qualification workflow
explicitly builds and repairs for ``manylinux_2_28``.

macOS
~~~~~

The Linux helper is not the macOS build path. Use the native build frontend with
the experimental CMake gate and one explicit architecture. This example builds
minimal for Apple Silicon; it is a development path awaiting fresh qualification
for the current source:

.. code-block:: console

   MACOSX_DEPLOYMENT_TARGET=11.0 ARCHFLAGS="-arch arm64" \
   python -m build --wheel --no-isolation --outdir dist/macos-arm64-minimal \
     -Cbuild-dir=build/gmatpy/macos-arm64-minimal \
     -Ccmake.define.CSPICE_DIR=/absolute/path/to/cspice \
     -Ccmake.define.GMAT_PY_PROFILE=minimal -Cwheel.build-tag=1minimal \
     -Ccmake.define.GMAT_PY_EXPERIMENTAL_MACOS=ON \
     -Ccmake.define.CMAKE_OSX_ARCHITECTURES=arm64 \
     -Ccmake.define.CMAKE_OSX_DEPLOYMENT_TARGET=11.0
   delocate-wheel --require-archs arm64 -w wheelhouse dist/macos-arm64-minimal/*.whl

For a native Intel build, change the architecture and architecture-specific paths
to ``x86_64``. For extended, change both the profile and tag to ``extended`` and
``2extended`` and use a separate build directory. Universal2 and cross-compiled
builds are not covered. Do not share native build directories or CSPICE libraries
between architectures or profiles.

For any direct build frontend, always pair ``GMAT_PY_PROFILE`` with its
``wheel.build-tag``. Validate and test the resulting installed wheel as described
in :doc:`development`, then continue with :doc:`quickstart`.
