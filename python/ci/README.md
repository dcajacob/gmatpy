# Native portability qualification (experimental)

`qualify.py` builds one full headless wheel, with SPICE and all 17 packaged data
files, from a single frozen sdist using the exact standard-ABI CPython
interpreter pinned in `interpreters.json`. The expansion pins 3.12.15, 3.13.16
and 3.14.8 for the twelve core ABI/target cells, followed by four 3.15.0
assessment cells. `prepare_interpreter.py` verifies each standalone interpreter
archive's hash, version and GIL mode; do not substitute the older interpreters
preinstalled in the Linux images. Run with `requirements.txt` in a fresh tools
virtualenv created by the selected interpreter. The required driver option
`--python-minor` identifies its matching manifest entry.
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

The wheel must also pass `check_distribution.py --release --source-manifest ...`.
Every failure stops qualification; there is no accepted owner-hold failure.
The log is `extended/release-preflight.log`, and completed results record
`release_preflight: passed`. The adopted published-software determination and its
scope are retained in `python/gmatpy/licenses/EXPORT_DETERMINATION.md` and
`EXPORT_DETERMINATION.json`. Qualification checks the final artifact and manifest;
it does not replace that recorded determination or extend it to different inputs.

GitHub qualification uses only public standard runner compute and read-only
contents/actions tokens, with at most two native runners concurrently. It has
no publishing secrets, OIDC, persistent build cache or package-release step.
Explicit budget confirmation enables at most one source and sixteen candidate
artifacts, with one-day retention and bounded payloads under the approved $0.02
aggregate storage cap. No free account storage allowance is assumed. Verified
copies and receipts are preserved locally before hosted copies are deleted;
the shared source stays available until all consumers finish. Public source
sharing is recorded in `PUBLIC_SOURCE_DECISION.md`; the scoped adopted product
determination and new PyPI publication approval remain separate.

The 0.2.1.dev0 candidate from source
`f8d8e4ce997ca7400afbe035b7ec55bd66c02575` passed all sixteen cells, with 209
tests plus three subtests per wheel and the numerical/artifact checks below.
The two Linux 3.13 cells are in initial run 38998592411; bounded recovery
38999648051 reused that exact source and verified both successes before
qualifying the remaining fourteen wheels. A standalone macOS CA-path failure
was repaired in workflow-only revision 54378760 without disabling TLS checks.
The current workflow propagates the existing bootstrap Python verified CA file
through `SSL_CERT_FILE`; it does not install or alter system trust.

An independent offline Linux x86 CPython 3.13.16 rebuild using the same
`/output/interpreter` header prefix reproduced the entire hosted wheel:
SHA256 `d7c6ee2d40158adaa47a75250df6a6f9a04e77d5a8424120c54bddbb99a3987e`,
all 60 members identical, with fresh installed/numerical checks passing.
This is a scoped reproduction result, not a claim across different compilers
or every target. Documentation-only successor commits do not relabel the
frozen candidate's source receipt. No new PyPI publication is implied.

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

## Published 0.2.1 binary reuse

Packaging source `6b5c286cfbd64500a848277aeed0aee9b2e440fc` reuses all sixteen qualified f8 native builds without recompilation or repair. All 17 published files match the fixed allowlist; every final wheel passed 209 tests plus 3 subtests before publication (https://github.com/dcajacob/gmatpy/actions/runs/39008578034) and after fresh native PyPI installation (https://github.com/dcajacob/gmatpy/actions/runs/39010062762). Publication receipt: https://github.com/dcajacob/gmatpy/actions/runs/39009509178. Original native/source/dependency/interpreter receipts remain separate from new packaging provenance. The protected staging job receives temporary contents:write only for draft GET access; installed verification is read-only and publication uses contents/actions read plus OIDC. The post-PyPI matrix uses contents:read only and retains no artifacts. Windows/free-threaded and older-host execution limits are unchanged.

## Windows x64 0.2.1 addition

Source `ae25a632d778172ab9570fd5c284968c2eba08bc` freshly rebuilt GMAT and all
2229 official Windows CSPICE N0067 sources on Windows Server 2022 x64. Standard
CPython 3.12.10/3.13.16/3.14.8/3.15.0 each passed 203 tests + 3 subtests with 6 expected
platform skips, installed-byte/PE/source/data checks and numerical/spline
regressions in https://github.com/dcajacob/gmatpy/actions/runs/40465394325.
Separate public TLE Tailor main integration on 3.14 passed 46 adapter tests and the
mandatory CPU JAX fit in https://github.com/dcajacob/gmatpy/actions/runs/40467329927.
Exact allowlists and source compatibility are in `.github/release/`; the Windows
native origin is distinct from Linux/macOS f8 reuse. All 1176 scientific/runtime/
build records match the published 0.2.1 sdist; existing PyPI files remain immutable.
The existing `publish-pypi.yml` / protected `pypi` environment publishes only
missing exact Windows files; `verify-windows-pypi-021.yml` tests public index
installs. Direct MSISE spline/ARM64/free-threaded/other Windows hosts remain outside
this Windows evidence. See `docs/windows.rst` for scoped claims and receipts.
