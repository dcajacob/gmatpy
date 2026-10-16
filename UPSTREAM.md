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

The subsequent remediation retains independently replaced numerical routines,
curated data and notices, headless packaging/profiles, and individually reviewed
engine corrections. The shared-core decision inventory is in
`python/ci/MIGRATION_CORE_REVIEW.json`. Qt UI/debugger/plot routing and startup
snapshot APIs are excluded. Original copyright and modification notices remain.

For later updates, add `upstream` using the URL above, fetch it, and create a
separate integration branch from this project's main. Review and merge the
chosen NASA commit, resolve curated-data and component-notice changes explicitly,
and regenerate the source identity. Run both profiles and numerical/source/data
checks before merging. Keep published main history stable; do not rebase it onto
a later NASA tip or import the former mixed Qt branch.
