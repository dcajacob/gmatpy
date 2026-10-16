"""Small three-source native differential probe; never builds the GMAT engine.

Usage: python probe_atmosphere_brent.py --repo REPO --f2c-root CSPICE_ROOT
       --output NEW_DIRECTORY [--with-scipy]
The candidate uses working-tree bytes, NASA/reference use immutable git blobs.
"""
import argparse
import ctypes as C
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shlex
import subprocess
import sys


NASA = "9363e129be366520c6edb0b4079204ed60666007"
REFERENCE = "50f61a05a1dd68ba2682d74a8631eba1b514630e"
FILES = ("src/base/solarsys/msise90_sub.c",
         "src/gmatutil/util/interpolator/BrentDekkerZero.cpp",
         "src/gmatutil/util/interpolator/BrentDekkerZero.hpp")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(item) for item in value]
    return value


WRAPPER = r'''#include "BrentDekkerZero.hpp"
#include "MessageInterface.hpp"
#include <exception>
#include <string>
int MessageInterface::calls = 0;
static thread_local std::string error;
extern "C" {
void* make() { return new BrentDekkerZero; }
void* copy(void* p) { return new BrentDekkerZero(*(BrentDekkerZero*)p); }
void assign(void* p, void* q) { *(BrentDekkerZero*)p = *(BrentDekkerZero*)q; }
void destroy(void* p) { delete (BrentDekkerZero*)p; }
int setup(void* p,double a,double b,double fa,double fb,double t) {
 try { ((BrentDekkerZero*)p)->SetInterval(a,b,fa,fb,t); return 0; }
 catch(const std::exception& e) { error=e.what(); return 1; }
}
int step(void* p,double x,double f,double* result) {
 try { *result=((BrentDekkerZero*)p)->FindStep(x,f); return 0; }
 catch(const std::exception& e) { error=e.what(); return 1; }
}
int more(void* p) {
 try { return ((BrentDekkerZero*)p)->CheckConvergence(); }
 catch(const std::exception& e) { error=e.what(); return -1; }
}
int driver(void* p,double a,double b,double t,double* result) {
 try { *result=((BrentDekkerZero*)p)->TestDriver(a,b,t); return 0; }
 catch(const std::exception& e) { error=e.what(); return 1; }
}
int messages() { return MessageInterface::calls; }
const char* message() { return error.c_str(); }
}
'''


class Solver:
    def __init__(self, library, pointer=None):
        self.lib = library
        self.pointer = self.lib.make() if pointer is None else pointer

    def __del__(self):
        self.lib.destroy(self.pointer)

    def setup(self, a, b, fa, fb, tolerance):
        if self.lib.setup(self.pointer, a, b, fa, fb, tolerance):
            raise ValueError(self.lib.message().decode())

    def step(self, point, value):
        result = C.c_double()
        if self.lib.step(self.pointer, point, value, C.byref(result)):
            raise ValueError(self.lib.message().decode())
        return result.value

    def more(self):
        result = self.lib.more(self.pointer)
        if result < 0:
            raise ValueError(self.lib.message().decode())
        return bool(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--f2c-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--with-scipy", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = args.repo.resolve()
    dependency = args.f2c_root.resolve()
    report = {"NASA": NASA, "reference": REFERENCE, "candidate": "working_tree",
              "script_sha256": digest(Path(__file__).read_bytes()),
              "python": sys.version, "sources": {}, "commands": [],
              "limits": "Sequential one-process compilation; no full GMAT build; 60s compile and 500 root-evaluation cap"}

    def run(command, cwd, timeout=60):
        report["commands"].append({"argv": [str(item) for item in command], "cwd": str(cwd)})
        completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout)
        with (output / "build.log").open("a") as log:
            log.write(completed.stdout + completed.stderr)
        completed.check_returncode()
        return completed.stdout

    cc = shlex.split(os.environ.get("CC", "cc"))
    cxx = shlex.split(os.environ.get("CXX", "c++"))
    report["compiler"] = run([*cxx, "--version"], output).splitlines()[0]
    report["f2c_dependency"] = {name: digest((dependency / name).read_bytes())
                               for name in ("include/f2c.h", "lib/cspice.a")}
    libraries = {}
    for label, revision in (("NASA", NASA), ("reference", REFERENCE), ("candidate", None)):
        directory = output / label
        directory.mkdir()
        for name in FILES:
            data = ((source / name).read_bytes() if revision is None else
                    subprocess.check_output(["git", "show", revision + ":" + name], cwd=source))
            (directory / Path(name).name).write_bytes(data)
            report["sources"][label + "/" + name] = digest(data)
        (directory / "utildefs.hpp").write_text("using Real=double; using Integer=int;\n#define GMATUTIL_API\n")
        (directory / "InterpolatorException.hpp").write_text(
            "#include <stdexcept>\nstruct InterpolatorException:std::runtime_error{using std::runtime_error::runtime_error;};\n")
        (directory / "MessageInterface.hpp").write_text(
            "#pragma once\nstruct MessageInterface{static int calls; template<class... T> static void ShowMessage(T...){++calls;}};\n")
        (directory / "wrapper.cpp").write_text(WRAPPER)
        run([*cxx, "-std=c++17", "-O2", "-fPIC", "-shared", "-I.",
             "BrentDekkerZero.cpp", "wrapper.cpp", "-o", "brent.so"], directory)
        run([*cc, "-O2", "-fPIC", "-shared", "-I" + str(dependency / "include"),
             "msise90_sub.c", str(dependency / "lib/cspice.a"), "-lm", "-o", "msise.so"], directory)
        brent = C.CDLL(str(directory / "brent.so"))
        brent.make.restype = C.c_void_p
        brent.copy.argtypes = [C.c_void_p]
        brent.copy.restype = C.c_void_p
        brent.assign.argtypes = [C.c_void_p, C.c_void_p]
        brent.destroy.argtypes = [C.c_void_p]
        brent.setup.argtypes = [C.c_void_p] + [C.c_double] * 5
        brent.step.argtypes = [C.c_void_p, C.c_double, C.c_double, C.POINTER(C.c_double)]
        brent.more.argtypes = [C.c_void_p]
        brent.driver.argtypes = [C.c_void_p, C.c_double, C.c_double, C.c_double, C.POINTER(C.c_double)]
        brent.message.restype = C.c_char_p
        libraries[label] = {"brent": brent, "msise": C.CDLL(str(directory / "msise.so"))}

    failures = []

    def check(name, condition):
        if not condition:
            failures.append(name)

    def solve(label, function, a, b, tolerance, first=None, trace=False):
        solver = Solver(libraries[label]["brent"])
        solver.setup(a, b, function(a), function(b), tolerance)
        point = b if first is None else first
        # NASA's convergence state is uninitialized until its first FindStep.
        history = []
        for count in range(500):
            previous, value = point, function(point)
            point = solver.step(point, value)
            if trace:
                history.append({"evaluated": previous, "value": value, "proposal": point})
            if not solver.more():
                result = {"root": point, "steps": count + 1, "residual": function(point)}
                if trace:
                    result["trajectory"] = history
                return result
        return {"root": point, "steps": 500, "nonconvergence": True}

    brent_results = {"named": {}, "family": []}
    for name, function, a, b, expected in (
            ("exact_interior", lambda x: x - 1., 0., 3., 1.),
            ("exact_left", lambda x: x, 0., 2., 0.),
            ("exact_right", lambda x: x - 2., 0., 2., 2.),
            ("sqrt2", lambda x: x*x - 2., 0., 2., math.sqrt(2.))):
        row = {label: solve(label, function, a, b, 1e-12, trace=True) for label in libraries}
        brent_results["named"][name] = row
        check("brent_" + name, abs(row["candidate"]["root"] - expected) <= 3e-12)

    brent_results["ordinary_trajectories"] = {}
    for name, function, a, b in (
            ("smooth_exponential", lambda x: math.exp(x) - 3., 0., 2.),
            ("NASA_demo_polynomial", lambda x: 3*x*x*x - x*x + 7*x - 6., 0., 1.)):
        brent_results["ordinary_trajectories"][name] = {
            label: solve(label, function, a, b, 1e-12, trace=True) for label in libraries}

    for scale in (1e-100, 1e-12, 1., 1e8, 1e100):
        for root in (-.7, -.01, 0., .01, .7):
            for kind in ("linear", "flat_cubic", "cubic", "exp"):
                for reverse in (False, True):
                    function = {"linear": lambda z: z, "flat_cubic": lambda z: z**3,
                                "cubic": lambda z: z + z**3, "exp": math.expm1}[kind]
                    f = lambda x: function(x / scale - root)
                    a, b = (scale, -scale) if reverse else (-scale, scale)
                    row = {"scale": scale, "expected": root * scale, "kind": kind, "reverse": reverse}
                    for label in libraries:
                        row[label] = solve(label, f, a, b, scale * 1e-13)
                        row[label]["scaled_error"] = abs(row[label]["root"] / scale - root)
                    check("brent_family_" + str(len(brent_results["family"])),
                          row["candidate"]["scaled_error"] < 1e-11 and
                          not row["candidate"].get("nonconvergence"))
                    brent_results["family"].append(row)

    candidate = libraries["candidate"]["brent"]
    contracts = {}
    for first, second in ((0., 2.), (2., 0.)):
        for initial in (first, second):
            value = solve("candidate", lambda x: x*x - 2., first, second, 1e-12, initial)
            check("brent_either_initial_endpoint", abs(value["root"] - math.sqrt(2.)) <= 3e-12)
    solver = Solver(candidate)
    for method in (lambda: solver.more(), lambda: solver.step(0., 0.)):
        try:
            method()
            failures.append("brent_pre_setup_rejection")
        except ValueError:
            pass
    for interval in ((0., 1., 1., 2., 1e-12), (0., 1., -1., 1., -1.),
                     (0., 1., -1., math.inf, 1e-12)):
        try:
            solver.setup(*interval)
            failures.append("brent_invalid_interval_rejection")
        except ValueError:
            pass
    solver.setup(0., 2., -2., 2., 1e-12)
    point = solver.step(2., 2.)
    copied = Solver(candidate, candidate.copy(solver.pointer))
    assigned = Solver(candidate)
    candidate.assign(assigned.pointer, solver.pointer)
    values = [obj.step(point, point*point - 2.) for obj in (solver, copied, assigned)]
    check("brent_copy_assignment_pending", values[0] == values[1] == values[2])
    tiny = math.ulp(0.)
    solver.setup(-tiny, tiny, -tiny, tiny, 0.)
    check("brent_subnormal_initial_convergence", solver.more())
    point = solver.step(tiny, tiny)
    check("brent_subnormal_zero", point == 0. and solver.step(point, 0.) == 0. and not solver.more())
    solver.setup(-1., 1., -1., 1., 1e-12)
    for point, value in ((2., 2.), (0., math.nan)):
        try:
            solver.step(point, value)
            failures.append("brent_invalid_evaluation_rejection")
        except ValueError:
            pass
    check("brent_recovery", solver.step(1., 1.) == 0. and solver.step(0., 0.) == 0.)
    result = C.c_double()
    check("brent_test_driver", candidate.driver(solver.pointer, 0., 1., 1e-12, C.byref(result)) == 0
          and abs(3*result.value**3 - result.value**2 + 7*result.value - 6) < 1e-10)
    check("brent_quiet", candidate.messages() == 0)
    contracts["candidate_log_messages"] = candidate.messages()
    contracts["TestDriver_root"] = result.value
    brent_results["contracts"] = contracts
    brent_results["summary"] = {label: {"max_scaled_error": max(row[label]["scaled_error"] for row in brent_results["family"]),
                                      "max_steps": max(row[label]["steps"] for row in brent_results["family"])}
                                 for label in libraries}

    F, I = C.c_float, C.c_int
    def floats(values):
        return (F * len(values))(*values)

    def evaluate(label, x, y, left_slope, right_slope, queries):
        lib = libraries[label]["msise"]
        x, y = floats(x), floats(y)
        n, left, right = I(len(x)), F(left_slope), F(right_slope)
        y2 = floats([0.] * len(x))
        status = lib.spline_(x, y, C.byref(n), C.byref(left), C.byref(right), y2)
        values, integrals = [], []
        for query in queries:
            q, value, integral = F(query), F(), F()
            lib.splint_(x, y, y2, C.byref(n), C.byref(q), C.byref(value))
            lib.splini_(x, y, y2, C.byref(n), C.byref(q), C.byref(integral))
            values.append(value.value)
            integrals.append(integral.value)
        return {"status": status, "y2": list(y2), "values": values, "integrals": integrals}

    spline_results = {"endpoint_cases": [], "analytic_cases": []}
    for values in ((1., 1e-20), (1e20, 1.), (1e8, 1e-8), (1e-20, 1e20)):
        expected = F(values[1]).value
        row = {"y": values, "query": 1., "expected_endpoint": expected}
        row.update({label: evaluate(label, [0., 1.], values, 1e30, 1e30, [1.]) for label in libraries})
        check("msise_exact_knot", row["candidate"]["values"][0] == expected)
        spline_results["endpoint_cases"].append(row)
    for width in (1e-20, 1., 1e20):
        x = [0., F(width).value]
        # A line must be represented independently of interval scale.
        queries = [F(x[1] * fraction).value for fraction in (-.25, 0., .25, .5, .75, 1., 1.25)]
        row = {"width": width, "queries": queries}
        row.update({label: evaluate(label, x, [1., 3.], 1e30, 1e30, queries) for label in libraries})
        expected = [1. + 2. * query / x[1] for query in queries]
        check("msise_scaled_line", max(abs(a-b)/(1+abs(b)) for a,b in zip(row["candidate"]["values"], expected)) < 1e-7)
        spline_results["analytic_cases"].append(row)
    width = F(1e-40).value
    for name, values, queries in (
            ("far_constant", [1., 1.], [-1e38, 1e38]),
            ("far_scaled_line", [1., 1. + 2**-23], [-1e-25, 1e-25])):
        queries = [F(query).value for query in queries]
        expected = [F(values[0] + query / width * (values[1] - values[0])).value for query in queries]
        row = {"name": name, "width": width, "queries": queries, "expected": expected}
        row.update({label: evaluate(label, [0., width], values, 1e30, 1e30, queries) for label in libraries})
        check("msise_" + name, row["candidate"]["values"] == expected)
        spline_results["analytic_cases"].append(row)
    spline_results["inherited_short_integral"] = {
        label: evaluate(label, [0., 1.], [1., 1.], 1e30, 1e30, [1e-8]) for label in libraries}
    # This is a known NASA/current integration limitation, not silently fixed.
    check("msise_integration_helper_unchanged", spline_results["inherited_short_integral"]["candidate"]["integrals"] ==
          spline_results["inherited_short_integral"]["reference"]["integrals"])

    if args.with_scipy:
        import numpy as np
        import scipy
        from scipy.interpolate import CubicSpline
        oracle = {"scipy": scipy.__version__, "numpy": np.__version__, "datasets": 0, "queries": 0,
                  "max_scaled_error": {label: 0. for label in libraries},
                  "max_integral_scaled_error": {label: 0. for label in libraries}}
        rng = random.Random(20261016)
        for count in (2, 3, 4, 5, 10, 100, 101):
            for mode in ("natural", "clamped", "mixed_left", "mixed_right"):
                for _ in range(4):
                    x = [0.]
                    for _ in range(count - 1):
                        x.append(F(x[-1] + rng.uniform(.01, 2.)).value)
                    y = [F(rng.gauss(0., 1.)).value for _ in x]
                    left = F(1e30 if mode in ("natural", "mixed_left") else rng.gauss(0., 1.)).value
                    right = F(1e30 if mode in ("natural", "mixed_right") else rng.gauss(0., 1.)).value
                    boundary = ("natural" if left > 9.9e29 else (1, left), "natural" if right > 9.9e29 else (1, right))
                    queries = [F(x[-1] * (-.25 + index * 1.5 / 26)).value for index in range(27)]
                    reference = CubicSpline(x, y, bc_type=boundary)
                    expected = reference(queries)
                    expected_integrals = reference.antiderivative()(queries) - reference.antiderivative()(x[0])
                    for label in libraries:
                        values = evaluate(label, x, y, left, right, queries)
                        error = max(abs(a-b)/(1+abs(b)) for a,b in zip(values["values"], expected))
                        oracle["max_scaled_error"][label] = max(oracle["max_scaled_error"][label], float(error))
                        integral_error = max(abs(a-b)/(1+abs(b)) for q,a,b in zip(queries, values["integrals"], expected_integrals) if q >= x[0])
                        oracle["max_integral_scaled_error"][label] = max(oracle["max_integral_scaled_error"][label], float(integral_error))
                    oracle["datasets"] += 1
                    oracle["queries"] += len(queries)
        check("msise_independent_scipy", oracle["max_scaled_error"]["candidate"] < 1e-5)
        spline_results["fresh_scipy"] = oracle

    atmosphere = {"cases": 0, "max_candidate_vs_reference_relative_density": 0.,
                  "max_candidate_vs_NASA_relative_density": 0., "max_reference_vs_NASA_relative_density": 0.,
                  "max_candidate_vs_reference_temperature_absolute": 0., "worst": None}
    def density(label, inputs):
        day, seconds, altitude, latitude, flux, ap = inputs
        args0 = [I(day), F(seconds), F(altitude), F(latitude), F(30.), F((seconds/3600.+2.) % 24.), F(flux), F(flux)]
        geomag, mass, d, t = floats([ap] * 7), I(48), floats([0.] * 8), floats([0.] * 2)
        libraries[label]["msise"].gtd6_(*(C.byref(v) for v in args0), geomag, C.byref(mass), d, t)
        return list(d), list(t)
    altitudes = (0., 10., 32.5, 62.5, 72.499, 72.5, 72.501, 89.999, 90., 90.001, 99.999, 100., 100.001,
                 109.999, 110., 110.001, 119.999, 120., 120.001, 150., 400.)
    for day in (26001, 26080, 26172, 26355):
        for seconds in (0., 43200.):
            for latitude in (-90., 0., 90.):
                for flux, ap in ((70., 0.), (150., 4.), (250., 100.)):
                    for altitude in altitudes:
                        inputs = (day, seconds, altitude, latitude, flux, ap)
                        values = {label: density(label, inputs) for label in libraries}
                        atmosphere["cases"] += 1
                        check("atmosphere_finite", all(math.isfinite(value) for pair in values.values() for group in pair for value in group))
                        for first, second in (("candidate", "reference"), ("candidate", "NASA"), ("reference", "NASA")):
                            error = abs(values[first][0][5] - values[second][0][5]) / abs(values[second][0][5])
                            name = "max_" + first + "_vs_" + second + "_relative_density"
                            if error > atmosphere[name]:
                                atmosphere[name] = error
                                if first == "candidate" and second == "reference":
                                    atmosphere["worst"] = {"inputs": inputs, "values": values}
                        atmosphere["max_candidate_vs_reference_temperature_absolute"] = max(
                            atmosphere["max_candidate_vs_reference_temperature_absolute"],
                            max(abs(a-b) for a,b in zip(values["candidate"][1], values["reference"][1])))
    check("ordinary_atmosphere_rounding", atmosphere["max_candidate_vs_reference_relative_density"] < 2e-6)
    report.update({"brent": brent_results, "splines": spline_results, "atmosphere": atmosphere,
                   "failures": failures, "passed": not failures})
    (output / "RESULTS.json").write_text(json.dumps(safe(report), indent=2, allow_nan=False) + "\n")
    print(json.dumps(safe({"passed": not failures, "failures": failures, "brent": brent_results["summary"],
                           "splines": spline_results.get("fresh_scipy"), "atmosphere": atmosphere}), indent=2))
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
