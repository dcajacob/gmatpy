# GMAT Py

GMAT Py is a standalone Python interface to the NASA GMAT astrodynamics engine.
It is an independently maintained derivative project. NASA's history and license
notices are preserved; NASA does not endorse this project.

The single headless package provides propagation, state/frame/time conversion,
native DE405, SPICE kernels, impulsive maneuvers, multiple spacecraft, bounded SMA
targeting and mission-script execution. It bundles the engine and 17 selected
scientific inputs. Finite-burn workflows use mission scripts. Discover the
supported boundary with `gmatpy.capabilities()`; optional plugins and a GUI are
not bundled.

See the [documentation](https://gmatpy.readthedocs.io/en/latest/),
[Python usage/build documentation](python/README.rst),
[capability details](python/PROFILES.rst), and
[native qualification](python/ci/README.md).

GMAT Py 0.2.0 is not yet published on PyPI. Install a matching candidate wheel
with `python -m pip install /path/to/gmatpy-0.2.0-<python>-<abi>-<platform>.whl`.
There is one standard wheel per supported Python ABI and platform; no feature
profile, build tag, or extra is needed.

This repository preserves NASA ancestry and maintains an explicit upstream update
path described in [UPSTREAM.md](UPSTREAM.md). Custom Qt GUI, debugger and viewer
work from the prior development line is excluded.

## Distribution status

Public source sharing for this dedicated repository is owner approved. Native
qualification is tracked by the manual GitHub Actions workflow. A successful test
run is not a product release clearance. The owner adopted the scoped CSPICE-derived
product determination on 2026-10-16, recorded in
`python/gmatpy/licenses/EXPORT_DETERMINATION.json` and marked resolved in
`CODE_MANIFEST.json`. Its applicability remains limited to the recorded scope;
package publication requires separate approval.

GMAT code uses Apache-2.0; third-party code and data have separate component terms.
Read [LICENSES.md](python/gmatpy/LICENSES.md),
[NOTICE.txt](python/gmatpy/NOTICE.txt), [NASA license](License.txt), and the
component/data manifests. Curated distribution artifacts exclude optional weather
inputs and the unreplaced historical Fortran spline source. Git history retains
upstream material; artifact exclusions do not erase history.

There is no package publishing, binary release upload, or automatic data refresh
in the qualification workflow. Ordinary test logs retain identities and hashes.
