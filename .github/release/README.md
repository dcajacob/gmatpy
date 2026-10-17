# TestPyPI publishing controls

The manual `publish-testpypi.yml` workflow accepts only the files named and
hashed in `testpypi-09eafabe.json`. Its upload destination is TestPyPI only.
There is no push, tag, release or build trigger, and the confirmation input
defaults to false. The protected `testpypi` environment requires owner review
and permits only the `main` branch. No long-lived upload token is stored.

## Artifact identity

The sdist contains packaging source `09eafabe3ff5063f0646d008a80bb70ae1d455c6`.
The wheels use that packaging inventory and updated documentation/manifest
prose while preserving native binaries compiled and qualified from
`b52941e9830940c3086839431fd1fb64812076ff`. No native recompilation is claimed.
Each wheel retains `BINARY_REUSE_PROVENANCE.json` in its dist-info directory,
including its original feasibility-operation label, original qualified-wheel
hash and three native-library hashes. Those exact repackaged bytes passed
source/release, RECORD, archive and binary checks; the refreshed x86_64 wheel
also passed a fresh 194-test run. Other-platform target installs were checked
locally, and their native runtime results remain attributed to b529.

`verify-testpypi-payload.py` verifies the fixed file hash, packaging inventory,
separate native-build identity and native-library hashes before publishing.
Updating this allowlist requires a reviewed artifact receipt. Do not substitute
an unqualified wheel, relabel old bytes as newly compiled, or reuse an uploaded
filename for different contents.

## Setup and first-upload boundary

The TestPyPI Trusted Publisher fields are project `gmatpy`, GitHub owner
`dcajacob`, repository `gmatpy`, workflow filename `publish-testpypi.yml` and
environment `testpypi`. Registering that publisher is a persistent TestPyPI
upload grant, separate from GitHub account linking and from approval to upload
a package. Verified account email and provider-required 2FA are prerequisites.
Do not configure a production PyPI publisher for this workflow.

The original remote qualification artifacts were deleted after local
verification. Before any dispatch, a separately approved staging process must
provide a real artifact ID from a successful first-attempt run in this
repository. Required name: `gmatpy-testpypi-09eafabe-<selection>`. The archive
contains exactly one root-level distribution file from the allowlist. Service
size is capped at 90,000,000 bytes, so staging can remain below the approved
276,000,000-byte simultaneous-storage limit by processing one file at a time.
Keep the existing aggregate spending limit and one-day retention boundary;
remove temporary copies promptly through the authorized cleanup process.

No first upload or release dispatch is authorized merely by adding this
workflow. After explicit approval, use its manual confirmation and environment
review gate, then independently verify TestPyPI's downloaded file hash and
installation. All files of a release are not uploaded atomically by this
single-file smoke-test workflow. Existing uploaded filenames cannot be replaced.

## GitHub-only staging

The separate manual `stage-testpypi.yml` job reads exactly one uploaded asset
from the unpublished draft `testpypi-staging-09eafabe`, targeting the exact
09eafabe packaging revision and owned by `dcajacob`. It checks the draft ID,
asset ID, single-file inventory, service digest, actual bytes and source/native
provenance before creating the artifact consumed by the existing publisher.
Both workflows require the protected `testpypi` environment and `main`.

Only the staging job has `contents:write` for authenticated draft visibility.
Its retrieval script uses GET requests only, and checkout does not retain
credentials. The job has no OIDC permission, no permanent token or secret,
and no build or package-publication step. The existing publishing job's
permissions and fixed TestPyPI endpoint remain unchanged.

Operate sequentially: upload one unchanged local candidate to the draft,
approve and verify its staging run, delete the exact draft asset, then approve
the publisher and verify its public download and installation before deleting
the exact Actions artifact. The trial's simultaneous temporary-storage cap is
171,000,000 bytes; a draft asset plus the 90,000,000-byte artifact cap fits
within it. Actions retention is one day. Draft assets do not expire
automatically: remove them on failure as well as success, and remove the empty
task-created draft and any task-created staging tag at completion. Preserve
receipts and the original local distributions. No Cloudflare or local service
is used. Separate upload approval remains required for each authorized trial.
