# Native portability qualification (experimental)

`qualify.py` builds one full headless wheel, with SPICE and all 17 packaged data
files, from a single frozen sdist
using standard-ABI CPython 3.14. Exact patch versions are recorded per target;
the pinned x86_64 image uses 3.14.7 and the pinned ARM64 image uses 3.14.8. Run with `requirements.txt` in a fresh tools virtualenv.
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
limits remain 2e-7 km position and 2e-10 km/s velocity. `reference-states.json`
was freshly sampled from NASA9363e129 scientific source with explicitly recorded
binding/build/startup adapters and exact common NASA inputs. Its embedded receipt
pins source, data, native libraries and sampling script. This is a NASA-source
comparison fixture, not an unmodified official NASA build or independent empirical
truth. The previous ERFA-based derivative reference is preserved byte-for-byte as
`reference-states-erfa-historical.json` (SHA256
`9e1436509a7f24c4246545a40d28f4ee0dd1a7edb8ca142c6c9f9e4e5cb5b303`).
The full test suite separately exercises the
numerical replacements and shutdown behavior. New run logs determine results;
previous Windows/Linux runs are historical evidence only.

All wheels must pass exact source provenance, notice/data hashes and exclusions,
binary checks and installed tests. The ordinary wheel filename has no profile
build tag. `BUILD_PROFILE.json` and the `profiles.extended` results key retain the
historical internal label for compatibility; they do not select distribution
variants. Stale `GMAT_PY_PROFILE` overrides other than `extended` are rejected.

`--release` records either a clean preflight or the unresolved
`cspice-derived-export-designation` owner item. Other failures stop qualification.
The owner must adopt a product export
determination bound to the final source/artifact hashes, entity, location and
jurisdiction, distribution scope and relevant input/contract facts. Tests and
NAIF toolkit classification do not make that owner determination. No assertion
of controlled input or universal filing requirement is made here.

Prepared GitHub runs use only public standard runner compute, read-only workflow
tokens, no secrets, cache, artifact upload or release. Artifact storage allowance
is unverified, so upload is disabled rather than assumed free. Public source sharing for the dedicated repository is owner approved, recorded
in PUBLIC_SOURCE_DECISION.md. The product release determination remains separate.
The workflow freezes clean immutable Git inputs; it does not publish packages.

Each native qualification also compiles a small harness against its installed GmatUtil
library and compares 320 spline cases / 9920 values with fixed independent SciPy
expectations at scaled tolerance 1e-10. These are fresh comparisons; reference
values are pre-recorded, with their generation script and hash retained.
The verifier additionally checks analytic/exact CubicSpline boundary, scale,
reuse and extrapolation cases. `verify_msise.py` compiles a tiny caller against
the installed GmatBase and checks analytic MSISE spline boundaries; it introduces
no runtime SciPy dependency. Neither check certifies every numerical input range.

Native behavior/default dispositions and bounded provenance observations are in
`CORE_BASELINE.md`. The common-data engine comparison also exercises native DE405,
explicit SPICE, ICRF gap/endpoints, EarthFixed/ITRF93 and one-day propagation.
Its detailed local source receipts and failed diagnostic runs are review evidence;
the small embedded reference is the durable CI regression subset.
