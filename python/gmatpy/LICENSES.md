# Code licenses and provenance

GMAT Py contains modified GMAT R2026a code under Apache License 2.0 and
statically linked CSPICE modules under separate NAIF terms. The machine-readable
record is [licenses/CODE_MANIFEST.json](licenses/CODE_MANIFEST.json). Scientific
data are tracked separately in `licenses/DATA_MANIFEST.json`.

- **GMAT:** include [Apache 2.0](licenses/GMAT.txt), retain applicable upstream
  notices, and mark changed inherited files. The dated modification comments
  identify differences from NASA commit
  `9363e129be366520c6edb0b4079204ed60666007`. Describing GMAT's origin does not
  imply NASA endorsement or confer trademark rights.
- **CSPICE N0067:** [NAIF-CSPICE.txt](licenses/NAIF-CSPICE.txt) reproduces the
  official rules and disclaimer. They permit toolkit modules in a third-party
  SPICE-based tool, distinguish that from toolkit mirroring, and include separate
  modification, support, indemnity and export-designation provisions. Carry
  these terms with native distributions; resolve applicable release obligations.
- **f2c runtime:** the official CSPICE sources contain Netlib-origin runtime
  implementations, and the reference library contains their corresponding
  objects and symbols. Preserve [F2C.txt](licenses/F2C.txt), including copyright,
  permission and disclaimer. This conclusion comes from runtime source/object
  evidence, rather than the translator or `f2c.h` alone.
- **SWIG:** [SWIG.txt](licenses/SWIG.txt) records the installed 4.5.0 license.
  Generated support code may use chosen distribution terms. SWIG is a build
  dependency; distributing the generator itself would require its separate
  license compliance.
- **Host runtimes:** the reference Linux build obtains CPython and platform
  C/C++ runtimes from its host. Check each final/repaired wheel for copied
  libraries; bundled runtime copies need their own license records.

The code manifest records sources, hashes, evidence, build exclusions and
remaining checks. The inspected local CSPICE library differs from the official
precompiled archive, so the comparison does not prove exact source-to-binary
correspondence. Recheck the dependency artifacts and linked objects for every
release. GUI, optimal-control, MATLAB and legacy Xerces components are outside
this headless configuration; enabling them requires a new inventory.

The project records the retained MSISE/CubicSpline replacements as derived from
endpoint and continuity equations. NASA's MSISE routines explicitly identify
Numerical Recipes adaptations; CubicSpline has specific procedural references.
The publisher's restrictive terms are documented, but their applicability and
separate permissions for NASA's exact implementations were not determined.
Retaining these replacements is a scoped provenance choice, not a demonstrated
legal requirement or a Python dependency. Their endpoint/scale regressions are
repaired separately from that choice. Tests validate selected behavior; they do
not authenticate independent authorship, source exposure or a clean-room process.
The historical `msise90_sub.for` remains in Git history and is excluded from
curated source archives.

Brent-Dekker returns to NASA's solver structure with focused state, exact-root,
input and headless safeguards. Its inherited citation to spline pages alone
does not establish a licensing need for a wholesale root-finder rewrite.
NotAKnot's retained changes are comments only. Jacchia-Roberts polynomial
deflation remains unchanged from NASA with its original credits and reference;
that citation alone does not establish copying or applicable publisher terms.
See `python/ci/CORE_BASELINE.md` in source and the code manifest for exact
component dispositions and the limits of this review.

Scientific data carry component-specific records. NGA EGM96 uses the agency's
public-information copying policy. JGM legacy variants and the rebuilt native
DE405 numerical records have a documented U.S. factual-data assessment, rather
than an invented provider license; see [GRAVITY-DATA.txt](licenses/GRAVITY-DATA.txt)
and [JPL-EPHEMERIS-NUMERIC.txt](licenses/JPL-EPHEMERIS-NUMERIC.txt). NAIF kernels
follow unchanged/modified-kernel rules. NASA's original ICRF values/grid and
March Earth PCK snapshot are the defaults. ERFA-derived 1980 nutation
coefficients retain its BSD notice; optional ERFA ICRF generation is separate.
Exact inputs, reuse bases and coverage are in the data manifest. Optional
weather/troposphere inputs remain excluded.

The separately recorded release action is the responsible owner's product-specific
export determination under NAIF's derived-product provision. The toolkit's TSPA
designation cannot simply be inherited. The published rules do not prescribe a
universal government filing or lawyer approval. Owner facts and applicable
jurisdiction must support the adopted decision; no designation is assigned here.

Component observations remain bounded as described above and in the manifest.
These are targeted engineering/provenance records, not a worldwide legal
guarantee or an exhaustive review of every inherited routine. Future dependencies
and build configurations can change the applicable terms.
