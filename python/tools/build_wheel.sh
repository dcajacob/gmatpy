#!/usr/bin/env bash
# Build a self-contained Linux wheel. Run inside a manylinux image for distribution.
set -euo pipefail

task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
python_bin="${HPOP_PYTHON:-python3}"
output_root="${HPOP_WHEEL_DIR:-${task_root}/wheelhouse}"
: "${CSPICE_DIR:?Set CSPICE_DIR to a PIC CSPICE include/ and lib/ tree}"
parallelism="${CMAKE_BUILD_PARALLEL_LEVEL:-4}"
mkdir -p "${output_root}"

cd "${task_root}"
export CMAKE_BUILD_PARALLEL_LEVEL="${parallelism}"
"${python_bin}" -m build --wheel --no-isolation \
  -Ccmake.define.CSPICE_DIR="${CSPICE_DIR}"
# Check only this build's repaired output, even when old wheels remain nearby.
repair_dir="$(mktemp -d "${output_root}/.repair-XXXXXXXX")"
trap 'rm -rf -- "${repair_dir}"' EXIT
"${python_bin}" -m auditwheel repair dist/gmat_hpop-0.1.0-*.whl -w "${repair_dir}"
for wheel in "${repair_dir}"/gmat_hpop-0.1.0-*.whl; do
  "${python_bin}" python/tools/check_wheel.py "${wheel}"
  mv -- "${wheel}" "${output_root}/"
done
