#!/usr/bin/env bash
# Build a self-contained Linux wheel. Run inside a manylinux image for distribution.
set -euo pipefail

task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
python_bin="${HPOP_PYTHON:-python3}"
dependency_root="${HPOP_DEPENDENCY_DIR:-${task_root}/build/hpop-dependencies}"
output_root="${HPOP_WHEEL_DIR:-${task_root}/wheelhouse}"
: "${CSPICE_DIR:?Set CSPICE_DIR to a PIC CSPICE include/ and lib/ tree}"
parallelism="${CMAKE_BUILD_PARALLEL_LEVEL:-4}"
mkdir -p "${dependency_root}" "${output_root}"

# System Xerces often pulls in ICU, curl, TLS and LDAP. Build a small local
# parser instead; headless propagation requires none of those capabilities.
archive="${dependency_root}/xerces-c-3.2.5.tar.gz"
if [[ ! -f "${archive}" ]]; then
  curl --fail --location --retry 2 \
    https://archive.apache.org/dist/xerces/c/3/sources/xerces-c-3.2.5.tar.gz \
    --output "${archive}"
fi
printf '%s  %s\n' \
  '545cfcce6c4e755207bd1f27e319241e50e37c0c27250f11cda116018f1ef0f5' \
  "${archive}" | sha256sum --check -
source_dir="${dependency_root}/xerces-c-3.2.5"
if [[ ! -d "${source_dir}" ]]; then
  tar -xzf "${archive}" -C "${dependency_root}"
fi
prefix="${dependency_root}/xerces-install"
cmake -S "${source_dir}" -B "${dependency_root}/xerces-build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DCMAKE_INSTALL_PREFIX="${prefix}" -DCMAKE_INSTALL_LIBDIR=lib -DBUILD_SHARED_LIBS=ON \
  -Dnetwork:BOOL=OFF -Dtranscoder=iconv -Dmessage-loader=inmemory -DBUILD_TESTING=OFF
cmake --build "${dependency_root}/xerces-build" --parallel "${parallelism}"
cmake --install "${dependency_root}/xerces-build"

cd "${task_root}"
export CMAKE_BUILD_PARALLEL_LEVEL="${parallelism}"
"${python_bin}" -m build --wheel --no-isolation \
  -Ccmake.define.CSPICE_DIR="${CSPICE_DIR}" \
  -Ccmake.define.XercesC_INCLUDE_DIR="${prefix}/include" \
  -Ccmake.define.XercesC_LIBRARY_RELEASE="${prefix}/lib/libxerces-c-3.2.so" \
  -Ccmake.define.HPOP_XERCES_SOURCE_DIR="${source_dir}"
export LD_LIBRARY_PATH="${prefix}/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
"${python_bin}" -m auditwheel repair dist/gmat_hpop-0.1.0-*.whl -w "${output_root}"
for wheel in "${output_root}"/gmat_hpop-0.1.0-*.whl; do
  "${python_bin}" python/tools/check_wheel.py "${wheel}"
done
