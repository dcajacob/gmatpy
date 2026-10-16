#!/usr/bin/env bash
# Build a self-contained Linux wheel. Run inside a manylinux image for distribution.
set -euo pipefail

task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
python_bin="${GMAT_PY_PYTHON:-python3}"
output_root="${GMAT_PY_WHEEL_DIR:-${task_root}/wheelhouse}"
parallelism="${CMAKE_BUILD_PARALLEL_LEVEL:-2}"
if [[ ${GMAT_PY_PROFILE+x} && "${GMAT_PY_PROFILE:-}" != extended ]]; then
  echo "GMAT_PY_PROFILE=${GMAT_PY_PROFILE} is obsolete; GMAT Py builds one full headless package (SPICE included)" >&2
  exit 2
fi
unset GMAT_PY_PROFILE
: "${CSPICE_DIR:?Set CSPICE_DIR to a PIC CSPICE include/ and lib/ tree}"
mkdir -p "${output_root}"
output_root="$(cd -- "${output_root}" && pwd)"

cd "${task_root}"
export CMAKE_BUILD_PARALLEL_LEVEL="${parallelism}"
# Artifact contents are always checked. Publication requires a separate
# check_distribution.py --release run resolving the manifest's pending terms.
build_dir="$(mktemp -d "${output_root}/.build-XXXXXXXX")"
cleanup() {
  status=$?
  if [[ ${status} -eq 0 ]]; then
    rm -rf -- "${build_dir}"
  else
    echo "Build failed; retained intermediate outputs: ${build_dir}" >&2
  fi
}
trap cleanup EXIT
# Both inputs and repaired outputs belong to this invocation. A stale wheel in
# dist/ must never be repaired, tested or returned as the current candidate.
"${python_bin}" -m build --wheel --no-isolation --outdir "${build_dir}/raw" \
  -Ccmake.define.CSPICE_DIR="${CSPICE_DIR}" \
  -Cbuild-dir="${GMAT_PY_BUILD_DIR:-${build_dir}/native}"
shopt -s nullglob
wheels=("${build_dir}"/raw/*.whl)
if [[ ${#wheels[@]} -ne 1 ]]; then
  echo "Expected exactly one wheel from this build" >&2
  exit 1
fi
provenance_args=()
if [[ -f python/gmatpy/BUILD_PROVENANCE.json ]]; then
  provenance_args=(--source-manifest python/gmatpy/BUILD_PROVENANCE.json)
fi
if [[ "${GMAT_PY_REPAIR:-1}" == 0 ]]; then
  # Explicitly requested local Linux candidate; no manylinux compatibility claim.
  "${python_bin}" python/tools/check_wheel.py "${wheels[0]}" "${provenance_args[@]}"
  mv -- "${wheels[0]}" "${output_root}/"
  exit 0
fi
"${python_bin}" -m auditwheel repair "${wheels[0]}" -w "${build_dir}/repaired"
repaired=("${build_dir}"/repaired/*.whl)
if [[ ${#repaired[@]} -ne 1 ]]; then
  echo "Expected exactly one repaired wheel" >&2
  exit 1
fi
for wheel in "${repaired[@]}"; do
  "${python_bin}" python/tools/check_wheel.py "${wheel}" "${provenance_args[@]}"
  mv -- "${wheel}" "${output_root}/"
done
