"""Analytic MSISE spline boundaries against the installed GmatBase library.

Usage: python verify_msise.py SOURCE_DIRECTORY NEW_OUTPUT_DIRECTORY
No SciPy dependency and no GMAT engine rebuild. The native harness only calls
the installed library's C spline routines; the equations/expected values below
are independent exact-line and exact-cubic invariants.
"""
import ctypes as C
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import sys

import gmatpy


HARNESS = r'''#include <cstdint>
static_assert(sizeof(float) == 4 && sizeof(std::int32_t) == 4, "MSISE f2c ABI");
extern "C" int spline_(float*,float*,std::int32_t*,float*,float*,float*);
extern "C" int splint_(float*,float*,float*,std::int32_t*,float*,float*);
extern "C" int evaluate_msise(float* x,float* y,std::int32_t n,float left,
                             float right,float* queries,std::int32_t count,float* output) {
   if (n < 2 || n > 101) return 2;
   float second[101];
   int status = spline_(x,y,&n,&left,&right,second);
   if (status) return status;
   for (std::int32_t i=0; i<count; ++i) {
      status = splint_(x,y,second,&n,&queries[i],&output[i]);
      if (status) return status;
   }
   return 0;
}
'''


def main():
    source = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    native = Path(gmatpy.__file__).resolve().parent / "_native"
    mac = platform.system() == "Darwin"
    if platform.system() not in ("Linux", "Darwin"):
        raise RuntimeError("Installed MSISE harness currently requires Linux/macOS")
    libraries = list(native.glob("libGmatBase.dylib" if mac else "libGmatBase.so.*"))
    assert len(libraries) == 1, libraries
    library = libraries[0]
    compiler = shutil.which("clang++" if mac else "g++")
    assert compiler
    harness = output / ("msise-harness.dylib" if mac else "msise-harness.so")
    harness_source = output / "msise-harness.cpp"
    harness_source.write_text(HARNESS)
    command = [compiler, "-dynamiclib" if mac else "-shared", "-fPIC", "-std=c++17", "-O2"]
    if mac:
        command += ["-arch", platform.machine(), "-mmacosx-version-min=11.0"]
    command += [str(harness_source), str(library), "-Wl,-rpath," + str(native), "-o", str(harness)]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (output / "compile.log").write_text(completed.stdout + completed.stderr)
    completed.check_returncode()
    function = C.CDLL(str(harness)).evaluate_msise
    ptr = C.POINTER(C.c_float)
    function.argtypes = [ptr, ptr, C.c_int32, C.c_float, C.c_float, ptr, C.c_int32, ptr]
    records = []

    def check(name, x, y, queries, expected, left=1e30, right=1e30, exact=False):
        arrays = [(C.c_float * len(values))(*values) for values in (x, y, queries)]
        values = (C.c_float * len(queries))()
        assert function(arrays[0], arrays[1], len(x), left, right, arrays[2], len(queries), values) == 0, name
        expected = [C.c_float(value).value for value in expected]
        errors = [abs(a-b)/(1+abs(b)) for a,b in zip(values, expected)]
        passed = list(values) == expected if exact else max(errors) < 2e-7
        records.append({"name": name, "x": list(arrays[0]), "y": list(arrays[1]), "queries": list(arrays[2]),
                        "expected": expected, "actual": list(values), "exact": exact,
                        "maximum_scaled_error": max(errors), "passed": passed})

    for y in ([1., 1e-20], [1e20, 1.], [1e8, 1e-8], [1e-20, 1e20]):
        check("two-knot exact endpoints", [0., 1.], y, [0., 1.], y, exact=True)
    for width in (1e-20, 1., 1e20):
        width = C.c_float(width).value
        queries = [C.c_float(width * value).value for value in (-.25, 0., .25, .5, .75, 1., 1.25)]
        check("scaled line including extrapolation", [0., width], [1., 3.], queries,
              [1. + 2. * query / width for query in queries])
    width = C.c_float(1e-40).value
    check("far extrapolation preserves constant", [0., width], [1., 1.], [-1e38, 1e38], [1., 1.], exact=True)
    queries = [C.c_float(value).value for value in (-1e-25, 1e-25)]
    check("far extrapolation of scaled linear segment", [0., width], [1., 1. + 2**-23], queries,
          [1. + query / width * 2**-23 for query in queries], exact=True)
    check("far clamped quadratic preserves equal endpoint curvatures", [0., 2**-60], [0., 2**-120],
          [-1e10, 1e10], [1e20, 1e20], left=0., right=2**-59, exact=True)
    knots = [0., .25, .5, .75, 1.]
    ordinates = [value**3 for value in knots]
    queries = [-.25, 0., .125, .25, .375, .5, .625, .75, .875, 1., 1.25]
    check("clamped analytic cubic including extrapolation", knots, ordinates, queries,
          [value**3 for value in queries], left=0., right=3.)
    check("all tabulated cubic knots exact", knots, ordinates, knots, ordinates, left=0., right=3., exact=True)
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    result = {"cases": len(records), "compared_values": sum(len(row["actual"]) for row in records),
              "passed": all(row["passed"] for row in records), "records": records,
              "installed_module": str(gmatpy.__file__), "library_sha256": sha(library),
              "source_msise_sha256": sha(source / "src/base/solarsys/msise90_sub.c"),
              "script_sha256": sha(Path(__file__)), "harness_sha256": sha(harness), "compile_command": command,
              "note": "Fresh analytic invariants against installed bytes; no saved SciPy values, atmospheric empirical truth, or integration-helper equivalence claim."}
    (output / "RESULTS.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("cases", "compared_values", "passed", "library_sha256")}, indent=2))
    assert result["passed"], [row["name"] for row in records if not row["passed"]]


if __name__ == "__main__":
    main()
