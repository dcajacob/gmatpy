# Native baseline decisions (2026-10-16)

Review baseline: NASA GMAT `9363e129be366520c6edb0b4079204ed60666007`.
Reviewed derivative parent: `50f61a05a1dd68ba2682d74a8631eba1b514630e`.
The later NASA `c9b78bd1` time/vector update is separate and is not included.
This follow-up reduces scientific defaults and failure-path behavior changes;
it does not claim complete equivalence to an official NASA application binary.

| Component | Disposition and reason |
| --- | --- |
| ICRF input | Restore NASA's exact numeric table and irregular sampling grid. ERFA-generated values/grid are an optional scientific change, unnecessary for Python. The historical generator is unidentified; the manifest records a bounded numeric-data reuse basis rather than a provider-license certification. |
| Earth high-precision PCK | Restore NASA's March 2026 snapshot, ending 2026-06-12. Updating to September is a separate data update. NAIF producer metadata and kernel redistribution rules are recorded. |
| Nutation | Preserve the implemented NASA coefficient records in original summation order. Unsupported/unused legacy sections remain excluded; no new nutation model is introduced. |
| Native DE405/SPK/atmosphere tables | Keep the repackaging: coefficient/segment payloads and parsed atmosphere numbers already equal NASA. Changed labels, containers and names do not require another scientific-model change. |
| SPICE individual unload | Restore NASA `UnloadKernel`, removing failed-unload whole-pool clear and lexical replay. Replay changed text-kernel precedence and removed untracked external kernels. A failed individual unload now has NASA's error/recovery limitations. |
| SPICE full reset | Retain explicit `kclear_c` in `UnloadAllKernels` as a bounded lifecycle safeguard when text-kernel files vanish. It clears the entire process-global pool, including externally furnished kernels and inserted values; clients must coordinate pool ownership. |
| CubicSpline/MSISE spline | Retain the project's equation-derived implementations while the specifically attributed inherited routines' origin/permissions remain unverified. This is a scoped provenance choice, not a demonstrated legal requirement or a Python dependency. Repair replacement endpoint cancellation and scale overflow with normalized evaluation, preserving exact tabulated endpoints. |
| Brent-Dekker | Restore NASA's solver structure with narrowly tested state, exact-root, input and headless safeguards. A stale citation to spline pages does not establish licensing necessity for a wholesale root-finder replacement. |
| NotAKnot | Executable implementation already equals NASA; retained edits clarify comments only. |
| Jacchia-Roberts deflation | Retain unchanged NASA source and its original credits/reference. A book citation alone does not prove copied protected expression or applicable publisher restrictions. |
| Fixed-width DE copies | Retain bounded copies. NASA uses C-string operations on binary fixed-width fields; this is a memory-safety safeguard, with no intended numerical change. |
| Selected weather | Retain source-selective validation and deferred attachment checks so constant-flux drag can run without excluded optional datasets. Supplied-file weather physics is unchanged. |
| Headless/profile/EOF | Retain updater-disabled startup, configured SPK filenames, explicit minimal-profile errors and stream `int_type` EOF handling. These support packaging, optional features and unsigned-char platforms. |
| Ownership/output paths | Temporarily retain the previously isolated FileManager ownership and ephemeris output-path safeguards. Their separate fork branches are listed in `UPSTREAM.md`; no upstream acceptance is implied. |

The four optional startup-identity, SMADot metadata, unperturbed TLONGDot and
SPICE diagnostic changes were removed in `b70c4fd`. Their NASA behavior remains,
including NASA's known zero unperturbed TLONGDot. A discovered inherited MSISE
short-interval integration issue is recorded as a NASA limitation, not silently
fixed in this cleanup.

The spline replacements' independent-origin statements are project assertions.
Source differences and numerical tests do not independently authenticate a
clean-room process, authorship or rights clearance. NASA distributes its C++
files under Apache-2.0; the specific MSISE adaptation comments and CubicSpline
procedural references are separately recorded in `CODE_MANIFEST.json`.
[NR's publisher terms](https://numerical.recipes/licenseinfo.html) restrict its
covered code, but applicability and separate permissions for NASA's exact
implementations were not established. No blanket proprietary-code, infringement
or public-domain conclusion follows from these observations.

Validation must distinguish exact source/data identity, freshly executed paired
tests, historical saved expectations and untested behavior. Comparing a candidate
to an earlier derivative's saved propagation output does not establish NASA
equivalence. The independent SciPy spline expectations are historical; fresh
comparison runs must retain their original provenance. New source revisions need
new source receipts and both-profile qualification; earlier wheel hashes do not
qualify changed code or defaults.
