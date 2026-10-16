# GMAT Py 0.2.0 — adopted export determination

**Producer: Dan CaJacob, personally. Adopted 2026-10-16.** This records the
owner's supported product-specific determination for the reviewed full headless
scientific library. It is not government clearance or approval to upload to PyPI.
The companion [JSON record](EXPORT_DETERMINATION.json) supplies the checked
scope fingerprint and primary sources; `BUILD_PROVENANCE.json` identifies each
complete source build and final release receipts identify the actual artifacts.

## Determination and exact scope

For the reviewed unclassified scientific source and matching object code made
publicly available without further-dissemination restrictions, Dan adopts
**not subject to the EAR under 15 CFR 734.3(b)(3)(i) and 734.7**. This is a
publication-based scope exclusion. EAR99 instead describes an item still
subject to the EAR but absent from its Commerce Control List; no EAR99 label
is assigned here. The proposal is prospective for unpublished source/object
artifacts and applies to their qualifying public distribution.
[734.3](https://www.ecfr.gov/current/title-15/section-734.3),
[734.7](https://www.ecfr.gov/current/title-15/section-734.7).

The reviewed basis is commit `e224907b67e9532e8eb2e2f5955ac96a29a12a36`,
frozen source archive SHA256
`59c2f93c4ede0ddea9a9d419bb9564cbe3fd67d053360c94c0a24ed04b6103ef`.
The JSON fingerprint covers exact native/runtime/scientific-data and native
build inputs from that basis. The approved successor adds this record, resolves
the owner item and tightens qualification/documentation; it changes no reviewed
scientific payload. The artifact checker verifies that scope and the record's
hash, in addition to existing notices, data hashes, exclusions and complete
source provenance. New substantive functionality, dependencies or restricted
inputs require reassessment. An internal `extended` compatibility token does
not denote a second distribution.

## Facts and technical review

Dan confirmed personal release, and confirmed that the candidate contains no
nonpublic employer/client code or other restricted inputs. He expressly
adopted the supported determination and authorized the single-package GitHub
cleanup push and final builds. These are owner attestations; they do not
independently authenticate every inherited contributor's history. Location or
citizenship was not supplied or inferred. Its absence does not itself prevent
this U.S. publication-based item assessment.

The reviewed package contains the NASA-derived GMAT core, GMAT Py interface,
CSPICE N0067/f2c scientific modules, SWIG support and the 17 exact scientific
inputs in [DATA_MANIFEST.json](DATA_MANIFEST.json). It performs numerical orbit
propagation, state/time/frame conversion, maneuver simulation and semi-major-axis
goal solving. Trusted script/native entry points expose broader GMAT core
capabilities; no claim of sandboxing or inability to model spacecraft is made.
No reviewed weapon/missile-specific guidance or spacecraft command-uplink/TT&C
integration was identified. Component/license provenance remains separately
bounded in [CODE_MANIFEST.json](CODE_MANIFEST.json).

No recognized bundled confidentiality-encryption implementation was identified
in the packaged source, receipt-matched CSPICE C/header sources or retained
native symbols/dependencies/strings. SHA integrity checks and host HTTPS occur
in source build/validation helpers. Their use does not bundle the host TLS or
OpenSSL implementation. The installed runtime has no detected encryption or
network interface. Static inspection is not proof against unrecognized code.
Current 742.15(b)(2) specifically addresses public 5D002 source performing
non-standard cryptography; it is not a blanket open-source notification rule.
No such bundled functionality was identified here.
[742.15](https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C/part-742/section-742.15),
[734.17](https://www.ecfr.gov/current/title-15/section-734.17).

## Separate ITAR assessment

The reviewed functionality and owner-attested inputs identify no direct USML
defense-article or controlled technical-data relationship. The supported
disposition is ordinary scientific orbital-analysis software. Section 120.33
covers software directly related to defense articles; USML IV/XV require the
relevant enumerated-article relationship. Spacecraft terminology, numerical
maneuvers and targeting an orbital element alone do not establish that
relationship. This assessment does not presume the specially-designed
general-purpose release in 120.41(b)(5) applies to all spacecraft software.
[120.33](https://www.ecfr.gov/current/title-22/section-120.33),
[USML IV/XV](https://www.ecfr.gov/current/title-22/section-121.1),
[120.41](https://www.ecfr.gov/current/title-22/section-120.41).

ITAR's public-domain definition has separate routes. Public GitHub posting is
not treated as a cure for previously controlled material. No such material was
identified in the reviewed record; the conclusion rests on the independent
functionality/provenance assessment and owner inputs.
[120.34](https://www.ecfr.gov/current/title-22/section-120.34).

## SPICE and limits

NAIF permits modules in third-party tools and requires an outside producer's
own export designation. Its SPICE designation is not inherited by GMAT Py.
The rules do not prescribe universal government filing or lawyer approval;
BIS separately describes self-classification as an available route when
classification is needed. This record does not claim NAIF acceptance of this
particular procedure. No agency/provider filing or contact occurred.
[NAIF rules](https://naif.jpl.nasa.gov/naif/rules.html),
[BIS classification routes](https://www.bis.gov/licensing/classify-your-item).

This determination does not clear private pre-publication transfers,
mission-specific services, future caller scripts/plugins, other jurisdictions
or future modified products. Final native/dependency/repair bytes must be
inspected and receipted; the earlier retained-native fixture is not a newly
compiled release wheel. Numerical tests and a software license are separate
from export jurisdiction. Nothing here grants new copyright permissions,
government endorsement or a worldwide legal guarantee.

Primary sources were checked 2026-10-16. eCFR displayed Title 15 current through
October 14 and Title 22 through October 13 or 14 by page. Final publication remains
a separate authorized action after successful release/content checks.
