# Native portability qualification (experimental)

`qualify.py` builds both minimal and extended profiles from a single frozen sdist
using CPython 3.14.7. Run with `requirements.txt` in a fresh tools virtualenv.
It leaves native build trees, wheels, pytest logs, source/data/license checks,
installed-byte comparisons and numerical regression evidence under a fresh output
folder. It does not publish or upload anything. SOURCE_DATE_EPOCH=1790812800 fixes
archive timestamps; native wheels are not promised bit-identical across compilers.

Targets: Linux x86_64 and ARM64 in digest-pinned manylinux_2_28 containers; separate
macOS x86_64 and ARM64 builds on native macOS 15 runners. Never combine or reuse
native libraries across architectures. Linux ARM64 rebuilds the official Linux
CSPICE C sources with the LP64 configuration after removing x86-only `-m64`.
This is an experimental port, not an official NAIF ARM64 distribution. Every
platform rebuilds all 2229 CSPICE C files and executes type, endian and toolkit
version probes. `cspice-sources.json` pins the downloaded official packages.

macOS builds explicitly enable GMAT_PY_EXPERIMENTAL_MACOS, use one architecture
and target macOS 11.0. Library install IDs, relative load paths, dependencies,
minimum OS load commands and architecture are inspected after delocate repair.
Running on macOS 15 does not establish runtime support for macOS 11 through 14.
Linux repair explicitly requests manylinux_2_28; a repair failure must be fixed by
building against the old baseline, never by changing tags on newer binaries.

The numerical comparison includes DE405 propagation at 0, 60 (duplicate), 600s,
Earth ICRF/fixed transforms, gravity degree 70, drag, JGM3, and point mass. Absolute
limits are 2e-7 km position and 2e-10 km/s velocity. The reference is the earlier
qualified source tree 4e4c39e637a4da4f521be024359f84438462f5ab4b3dd16e11b725329b656167,
not an independent truth source. The full test suite separately exercises the
numerical replacements and shutdown behavior. New run logs determine results;
previous Windows/Linux runs are historical evidence only.

All wheels must pass exact source provenance, notice/data hashes and exclusions,
binary checks and installed tests. `--release` is deliberately expected to fail
only on `cspice-derived-export-designation`. The owner must adopt a product export
determination bound to the final source/artifact hashes, entity, location and
jurisdiction, distribution scope and relevant input/contract facts. Tests and
NAIF toolkit classification do not make that owner determination. No assertion
of controlled input or universal filing requirement is made here.

Prepared GitHub runs use only public standard runner compute, read-only workflow
tokens, no secrets, cache, artifact upload or release. Artifact storage allowance
is unverified, so upload is disabled rather than assumed free. Public source sharing for the dedicated repository is owner approved, recorded
in PUBLIC_SOURCE_DECISION.md. The product release determination remains separate.
The workflow freezes clean immutable Git inputs; it does not publish packages.
