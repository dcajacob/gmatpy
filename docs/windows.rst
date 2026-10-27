Windows x64 wheels
==================

The four standard-GIL CPython 3.12.10, 3.13.16, 3.14.8 and 3.15.0 Windows
x64 wheels passed native qualification and are approved for addition to
``gmatpy==0.2.1``. They preserve their exact qualified bytes. Publication uses
the existing protected PyPI workflow; the public release must contain their
fixed hashes before index installation is considered verified.

Use a matching standard x64 Python interpreter and request a wheel::

   py -3.14 -m pip install --only-binary=:all: gmatpy==0.2.1

Runtime requires the Microsoft C++ runtime (MSVCP140, VCRUNTIME140,
VCRUNTIME140_1 and Windows UCRT APIs). A compiler and a separate GMAT install
are unnecessary. Windows ARM64 and free-threaded Python are unqualified.

Build and source identity
-------------------------

`Native qualification <https://github.com/dcajacob/gmatpy/actions/runs/40465394325>`_
rebuilt all 2,229 official Windows CSPICE N0067 C sources, GMAT native libraries
and each Python binding on Windows Server 2022 x64, runner image
``20261022.344.1``, using MSVC 19.44.35229. The LLP64 ABI and toolkit version
were checked by executing a linked probe. The old f2c/UCRT declaration conflict
is handled by preincluding ``io.h``; the official C source bytes are unchanged.

The wheels embed source ``ae25a632d778172ab9570fd5c284968c2eba08bc``, source
archive SHA256 ``ee29b4c2ecc7e67a525709c8bc3c29c0197d1a739509eb2a3b89cbc1d060f414``.
They do not claim Linux/macOS native origin ``f8d8e4ce`` or packaging origin
``6b5c286c``. All 1,176 scientific/runtime/native/SWIG/build records match the
existing published 0.2.1 sdist exactly. The source differences are documentation,
CI helpers and qualification tests. Metadata identity/dependency headers match;
license-file header ordering and historical long-description prose are retained.
The existing PyPI sdist and sixteen Linux/macOS wheels remain unchanged.

The exact file/native hashes, immutable Actions artifact identities and complete
source comparison are recorded in
``.github/release/pypi-0.2.1-windows.json`` and
``.github/release/windows-source-compatibility-0.2.1.json``. No existing filename
may be replaced. The publisher verifies the qualified run and receipts, source
compatibility and every existing public file before uploading only missing
allowlisted Windows files. The existing ``pypi`` owner-review gate remains.

Executed checks
----------------

Every Windows wheel passed 203 tests plus three subtests, exact installed-byte
and import checks, x64 PE/dependency inspection, all seventeen data/notice inputs,
and release preflight. Six expected skips cover POSIX ``fork`` and the Unix
shell build helper. Saved-state comparison with the bounded NASA-source fixture
passed limits of ``2e-7 km`` position and ``2e-10 km/s`` velocity; the observed
maximum errors were ``9.095e-12 km`` and ``1.688e-14 km/s``. The installed C++
spline harness passed 320 reference cases / 9,920 values and seventeen analytic
cases. This is engineering regression evidence, not mission certification.
Direct MSISE C spline harness validation remains unexecuted because those helper
symbols are not exported by the Windows DLL; Jacchia-Roberts drag was exercised.

A separate fresh native Windows
`TLE Tailor integration <https://github.com/dcajacob/gmatpy/actions/runs/40467329927>`_
installed public main ``36be851c`` with this 3.14 wheel and ordinary required
JAX/JAXLIB 0.12.0.1 dependencies. All 46 adapter tests passed without skips;
mandatory CPU JAX with x64 enabled propagated GMAT states, converted them to TEME,
fit and exported a valid TLE. The public JAX example also passed. This check
covers Python 3.14 only, not broader Windows notebook or mission accuracy gates.

The separate ``verify-windows-pypi-021.yml`` workflow verifies the final public
hashes and installs ``gmatpy==0.2.1`` through the normal PyPI index in fresh native
Windows environments, then reruns installed-byte, import, suite and numerical
checks. Its completed run is the post-publication receipt. Windows desktop and
other Windows versions have not been newly executed by these Server 2022 tests.
