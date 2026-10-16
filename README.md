# GMAT Py

GMAT Py is a standalone Python interface to the NASA GMAT astrodynamics engine.
It is an independently maintained derivative project. NASA's history and license
notices are preserved; NASA does not endorse this project.

The headless package provides propagation, state/frame/time conversion, native
DE405 and access to engine interfaces. The extended profile adds SPICE kernels,
impulsive maneuvers, multiple spacecraft, bounded SMA targeting and mission-script
execution. Finite-burn workflows use mission scripts. Discover the installed
boundary with `gmatpy.capabilities()`; optional plugins and a GUI are not bundled.

See [Python usage/build documentation](python/README.rst),
[profile details](python/PROFILES.rst), and
[native qualification](python/ci/README.md).

This repository preserves NASA ancestry and maintains an explicit upstream update
path described in [UPSTREAM.md](UPSTREAM.md). Custom Qt GUI, debugger and viewer
work from the prior development line is excluded.

## Distribution status

Public source sharing for this dedicated repository is owner approved. Native
qualification is tracked by the manual GitHub Actions workflow. A successful test
run is not a product release clearance. The CSPICE-derived product determination
in `python/gmatpy/licenses/CODE_MANIFEST.json` remains owner dependent.

GMAT code uses Apache-2.0; third-party code and data have separate component terms.
Read [LICENSES.md](python/gmatpy/LICENSES.md),
[NOTICE.txt](python/gmatpy/NOTICE.txt), [NASA license](License.txt), and the
component/data manifests. Curated distribution artifacts exclude optional weather
inputs and the unreplaced historical Fortran spline source. Git history retains
upstream material; artifact exclusions do not erase history.

There is no package publishing, binary release upload, or automatic data refresh
in the qualification workflow. Ordinary test logs retain identities and hashes.
