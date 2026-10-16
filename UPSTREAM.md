# NASA upstream and derivative maintenance

Upstream: https://github.com/nasa/GMAT.git, branch `main`.
Initial NASA ancestor: `9363e129be366520c6edb0b4079204ed60666007`.
The clean derivative starts from this tested baseline. NASA main was observed at
`c9b78bd1c8499845cb78fde315e1f761b6b06f1c` during migration; that later UTC/vector
arithmetic update is not silently included in the baseline.

Four original Python commits were replayed with authorship and `cherry-picked-from`
identities preserved: `5cf0724054cb8d991f10eadc3d77c357c71acdef`,
`50bea1a28ce533f477c4c70d426cdb3a3c645e40`,
`ebdb841c90768dec215cc71616b3a9afc7af0579`, and
`3c35d1bd3425ea1b9e53accc296ca5fbea593a6c`.
Their previous mixed Qt parent is not an ancestor of this main branch.

The derivative retains independently replaced numerical routines, curated data
and notices, and headless packaging/profiles. The current shared-core disposition
inventory is `python/ci/MIGRATION_CORE_REVIEW.json`. Qt UI/debugger/plot routing
and startup snapshot APIs remain excluded. Original copyright and modification
notices remain.

The 2026-10-16 follow-up removes four optional general corrections from GMAT Py
and temporarily retains three downstream patches. The numbered fixes remain
separate on the dcajacob/GMAT fork for upstream review:

| Fix | GMAT Py disposition | Separate fork branch |
| --- | --- | --- |
| 01 FileManager ownership | Temporarily retained | [filemanager-ownership](https://github.com/dcajacob/GMAT/tree/upstream-fixes/20261016-filemanager-ownership) |
| 02 Startup identity | Removed; NASA getter behavior restored | [filemanager-startup-identity](https://github.com/dcajacob/GMAT/tree/upstream-fixes/20261016-filemanager-startup-identity) |
| 03 SMADot reported type | Removed; NASA type metadata restored | [smadot-type](https://github.com/dcajacob/GMAT/tree/upstream-fixes/20261016-smadot-type) |
| 04 Unperturbed TLONGDot | Removed; NASA parameter behavior restored | [tlongdot-unperturbed](https://github.com/dcajacob/GMAT/tree/upstream-fixes/20261016-tlongdot-unperturbed) |
| 05 Ephemeris output paths | Temporarily retained | [ephemeris-output-paths](https://github.com/dcajacob/GMAT/tree/upstream-fixes/20261016-ephemeris-output-paths) |
| 06 Selected weather inputs | Temporarily retained; required by the current absent-data constant-flux workflow | [drag-selected-weather](https://github.com/dcajacob/GMAT/tree/upstream-fixes/20261016-drag-selected-weather) |
| 07 SPICE diagnostics only | Removed; NASA diagnostic initialization restored | [spice-diagnostics-only](https://github.com/dcajacob/GMAT/tree/upstream-fixes/20261016-spice-diagnostics-only) |

The restored behaviors are observable through the native API and scripts.
`GetFullStartupFilePath()` again derives the startup directory from the caller's
current working directory and updates the stored directory. Constructing
`SMADot` again reports `EquinoctialSMADot` as its type. `TLONGDot` again reports
zero in the exact zero-perturbation case. SPICE diagnostic destination collisions
and unavailable output paths receive NASA's original handling; the fresh-sibling
selection and console fallback from patch 07 are no longer supplied.

These branch links identify work on an independent fork, not NASA acceptance or
merge records. Revisit temporary patches when the corresponding NASA changes
are reviewed and integrated. Whole-pool SPICE unload/cache recovery, numerical
replacements, scientific-data changes, minimal-profile guards, headless support
and packaging are outside this follow-up and remain unchanged. Restoring the
four NASA behaviors does not establish scientific equivalence for the entire
derivative. Each changed source revision requires new build provenance and
qualification; earlier results remain historical evidence.

For later updates, add `upstream` using the URL above, fetch it, and create a
separate integration branch from this project's main. Review and merge the
chosen NASA commit, resolve curated-data and component-notice changes explicitly,
and regenerate the source identity. Run both profiles and numerical/source/data
checks before merging. Keep published main history stable; do not rebase it onto
a later NASA tip or import the former mixed Qt branch.
