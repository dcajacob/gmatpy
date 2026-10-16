"""Validate the immutable final source and stage only approved retention files."""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import zipfile
from pathlib import Path

from packaging.utils import parse_wheel_filename

EXPECTED = {
    "source_revision": "0a26aaedbfac7b488bd3f2ae92bfdee5e825f37e",
    "git_tree_sha1": "154bd4bec4e46ee649f1eafe1f350a67c1055185",
    "working_tree_manifest_sha256": "62d23d0d737cfac0f87f9765c0519041b2dc12a63efdf02417ef29f403ec85d8",
    "source_tree_sha256": "d567f52d8802486172e5a8d28f730aa2ead222f519d971177c285740e53e81a6",
    "source_archive_sha256": "9b7b3c09796c522a22be8c82009de53c9a41765d15996314765eee6af9c29df3",
    "source_archive": "gmatpy-0.2.0.tar.gz",
    "source_date_epoch": "1792179570",
}
TARGETS = {
    "linux-arm64": {"manylinux_2_24_aarch64", "manylinux_2_28_aarch64"},
    "macos-arm64": {"macosx_11_0_arm64"},
    "macos-x86_64": {"macosx_11_0_x86_64"},
}
EVIDENCE = [
    "frozen/SOURCE_RECEIPT.json", "qualified/RESULTS.json",
    "qualified/EVIDENCE_SHA256.json", "qualified/CSPICE_BUILD_DEPENDENCY.json",
    "qualified/python-tools.txt", "qualified/sdist-check.log",
    *["qualified/extended/" + name for name in (
        "build.log", "repair.log", "binary-contents-check.log",
        "release-preflight.log", "install.log", "installed-bytes.log", "pytest.log",
        "states.json", "state-comparison.json", "spline.log", "spline/RESULTS.json",
        "msise.log", "msise/RESULTS.json")],
]
WHEEL_CAP = 90_000_000
EVIDENCE_CAP = 1_500_000
PAYLOAD_CAP = 91_500_000
SERVICE_ENVELOPE = 500_000  # per artifact, beyond the staged payload


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def regular(path):
    require(path.is_file() and not path.is_symlink(), "Not a regular file: " + str(path))
    require(not any(p.is_symlink() for p in path.parents), "Symlink parent: " + str(path))
    return path


def finite(value):
    if isinstance(value, float):
        require(math.isfinite(value), "Nonfinite evidence number")
    elif isinstance(value, dict):
        for v in value.values():
            finite(v)
    elif isinstance(value, list):
        for v in value:
            finite(v)


def load(path):
    value = json.loads(regular(path).read_text())
    finite(value)
    return value


def source_check(root):
    require(load(root / "frozen/SOURCE_RECEIPT.json") == EXPECTED,
            "Canonical source receipt differs")
    archive = regular(root / "frozen/artifacts" / EXPECTED["source_archive"])
    require(sha(archive) == EXPECTED["source_archive_sha256"], "Actual sdist differs")
    require(sha(regular(root / "frozen/WORKING_TREE.json")) ==
            EXPECTED["working_tree_manifest_sha256"], "Actual working manifest differs")
    print("CANONICAL_SOURCE_MATCH", json.dumps(EXPECTED), flush=True)


def stage(root, target, destination):
    require(target in TARGETS, "Unapproved target")
    require(not destination.exists(), "Staging destination must be new")
    require(os.environ.get("GITHUB_REPOSITORY") == "dcajacob/gmatpy", "Wrong repository")
    require(os.environ.get("GITHUB_RUN_ATTEMPT") == "1", "Only the first approved attempt may upload")
    require(os.environ.get("GITHUB_RUN_ID", "").isdigit(), "Missing run ID")
    require(re.fullmatch(r"[0-9a-f]{40}", os.environ.get("GITHUB_SHA", "")), "Missing orchestration SHA")
    source_check(root)
    result = load(root / "qualified/RESULTS.json")
    require(result["target"] == target, "Qualification target differs")
    require(result["sdist_sha256"] == EXPECTED["source_archive_sha256"] and
            result["source_tree_sha256"] == EXPECTED["source_tree_sha256"], "Qualification source differs")
    require(result["release_preflight"] == "passed", "Release preflight not passed")
    require(set(result["profiles"]) == {"extended"}, "Expected one full headless wheel")
    profile = result["profiles"]["extended"]
    require(re.fullmatch(r"192 passed in [0-9.]+s", profile["tests"]), "Unexpected tests or skips")
    state = profile["state_comparison"]
    require(state["position_tolerance_km"] == 2e-7 and state["velocity_tolerance_km_s"] == 2e-10,
            "State tolerances changed")
    require(state["maximum_position_error_km"] <= 2e-7 and state["maximum_velocity_error_km_s"] <= 2e-10,
            "State comparison failed")
    spline = profile["spline_comparison"]
    analytic = spline["analytic_regressions"]
    require(spline["cases"] == 320 and spline["compared_values"] == 9920 and
            spline["tolerance"] == 1e-10 and spline["maximum_scaled_error"] <= 1e-10,
            "Saved spline comparison failed")
    require(analytic["cases"] == 17 and analytic["compared_values"] == 54 and
            len(analytic["results"]) == 17 and all(r["passed"] and r["finite"] for r in analytic["results"]),
            "Analytic spline comparison failed")
    msise = profile["msise_comparison"]
    require(msise["cases"] == 12 and msise["compared_values"] == 51 and msise["passed"] and
            len(msise["records"]) == 12 and all(r["passed"] and r["finite"] for r in msise["records"]),
            "MSISE comparison failed")
    wheels = list((root / "qualified/extended/wheelhouse").iterdir())
    require(len(wheels) == 1, "Wheel directory must contain exactly one file")
    wheel = regular(wheels[0])
    require(wheel.stat().st_size <= WHEEL_CAP, "Wheel byte cap exceeded")
    name, version, build, tags = parse_wheel_filename(wheel.name)
    require(name == "gmatpy" and str(version) == "0.2.0" and not build, "Wrong project/version/build tag")
    platforms = {t.platform for t in tags}
    require(all(t.interpreter == "cp314" and t.abi == "cp314" for t in tags) and
            platforms <= TARGETS[target], "Wrong Python ABI or architecture")
    required_platform = "manylinux_2_28_aarch64" if target == "linux-arm64" else next(iter(TARGETS[target]))
    require(required_platform in platforms, "Required wheel platform tag missing")
    require(wheel.name == profile["wheel"] and wheel.stat().st_size == profile["bytes"] and
            sha(wheel) == profile["sha256"], "Qualified wheel bytes differ")
    with zipfile.ZipFile(wheel) as z:
        provenance_bytes = z.read("gmatpy/BUILD_PROVENANCE.json")
        provenance = json.loads(provenance_bytes)
        require(len(z.namelist()) == len(set(z.namelist())), "Duplicate wheel entries")
        require(all(not n.startswith("/") and ".." not in Path(n).parts for n in z.namelist()), "Unsafe wheel path")
    require(all(provenance[k] == EXPECTED[k] for k in (
        "source_revision", "source_tree_sha256", "working_tree_manifest_sha256")),
        "Embedded wheel source differs")
    dependency = load(root / "qualified/CSPICE_BUILD_DEPENDENCY.json")
    require(dependency["target"] == target and dependency["library_sha256"] == result["cspice_library_sha256"],
            "CSPICE dependency identity differs")
    names = list(EVIDENCE)
    if target == "linux-arm64":
        names += ["qualified/extended/auditwheel-before.log", "qualified/extended/auditwheel-after.log"]
    evidence_hashes = load(root / "qualified/EVIDENCE_SHA256.json")
    wheel_relative = wheel.relative_to(root).as_posix()
    names.append(wheel_relative)
    records = []
    for relative in names:
        path = regular(root / relative)
        digest = sha(path)
        if relative.startswith("qualified/") and relative != "qualified/EVIDENCE_SHA256.json":
            require(evidence_hashes[relative.removeprefix("qualified/")] == digest,
                    "Evidence hash differs: " + relative)
        records.append({"path": relative, "bytes": path.stat().st_size, "sha256": digest})
    evidence_bytes = sum(r["bytes"] for r in records if r["path"] != wheel_relative)
    require(evidence_bytes <= EVIDENCE_CAP, "Evidence byte cap exceeded")
    receipt = {"schema_version": 1, "repository": "dcajacob/gmatpy", "source": EXPECTED,
        "canonical_source_match": True, "orchestration_sha": os.environ["GITHUB_SHA"],
        "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF"), "run_id": os.environ["GITHUB_RUN_ID"],
        "attempt": 1, "job_key": os.environ.get("GITHUB_JOB"), "target": target,
        "python": result["python"], "platform": result["platform"],
        "wheel": {"filename": wheel.name, "bytes": wheel.stat().st_size, "sha256": sha(wheel),
                  "tags": sorted(map(str, tags)), "embedded_provenance_sha256": hashlib.sha256(provenance_bytes).hexdigest()},
        "cspice_library_sha256": result["cspice_library_sha256"],
        "cspice_dependency_receipt_sha256": sha(root / "qualified/CSPICE_BUILD_DEPENDENCY.json"),
        "release_preflight": "passed", "tests": profile["tests"], "files": records,
        "limits": {"wheel_bytes": WHEEL_CAP, "evidence_bytes": EVIDENCE_CAP,
                   "payload_bytes": PAYLOAD_CAP, "service_envelope_bytes": SERVICE_ENVELOPE},
        "receipt_self_hash": "Recorded separately in job output and local download index"}
    # Size fields converge without a recursive hash: the receipt inventories other files only.
    for _ in range(8):
        data = (json.dumps(receipt, indent=2) + "\n").encode()
        new = {"wheel_bytes": wheel.stat().st_size, "evidence_bytes": evidence_bytes + len(data),
               "receipt_bytes": len(data), "payload_bytes": sum(r["bytes"] for r in records) + len(data)}
        if receipt.get("totals") == new:
            break
        receipt["totals"] = new
    else:
        raise ValueError("Receipt size did not converge")
    require(new["evidence_bytes"] <= EVIDENCE_CAP and new["payload_bytes"] <= PAYLOAD_CAP, "Staged byte cap exceeded")
    require(new["payload_bytes"] + SERVICE_ENVELOPE <= 92_000_000, "Service envelope cap exceeded")
    destination.mkdir(parents=True)
    for record in records:
        dest = destination / record["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / record["path"], dest)
        require(sha(dest) == record["sha256"], "Copy differs: " + record["path"])
    (destination / "RETENTION_RECEIPT.json").write_bytes(data)
    print("RETENTION_READY", json.dumps({"target": target, "totals": new,
          "wheel_sha256": receipt["wheel"]["sha256"], "receipt_sha256": hashlib.sha256(data).hexdigest()}), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["source", "stage"])
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--target", choices=TARGETS)
    p.add_argument("--destination", type=Path)
    a = p.parse_args()
    if a.mode == "source":
        source_check(a.root)
    else:
        require(a.target is not None and a.destination is not None, "Stage requires target and destination")
        stage(a.root, a.target, a.destination)
