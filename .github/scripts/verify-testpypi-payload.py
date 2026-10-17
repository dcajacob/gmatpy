"""Retrieve one approved staging artifact and accept only exact qualified bytes."""
import argparse
import email.parser
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import tarfile
import zipfile

REPOSITORY = "dcajacob/gmatpy"
SOURCE = "09eafabe3ff5063f0646d008a80bb70ae1d455c6"
NATIVE_SOURCE = "b52941e9830940c3086839431fd1fb64812076ff"
SELECTIONS = ("sdist", "linux-x86_64", "linux-arm64", "macos-arm64", "macos-x86_64")
SERVICE_CAP = 90_000_000


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def check_context(environment):
    expected = {
        "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_WORKFLOW_REF": REPOSITORY + "/.github/workflows/publish-testpypi.yml@refs/heads/main",
    }
    require(all(environment.get(k) == v for k, v in expected.items()), "Unapproved workflow identity")


def check_manifest(manifest, selection):
    require(manifest["schema_version"] == 1 and manifest["project"] == "gmatpy"
            and manifest["version"] == "0.2.0" and manifest["candidate_source_revision"] == SOURCE
            and manifest.get("native_build_source_revision") == NATIVE_SOURCE
            and manifest.get("native_recompiled") is False,
            "Unapproved source/project")
    require(set(manifest["files"]) == set(SELECTIONS) and selection in SELECTIONS,
            "Unapproved payload selection")
    record = manifest["files"][selection]
    require(Path(record["filename"]).name == record["filename"]
            and 0 < record["bytes"] < SERVICE_CAP
            and re.fullmatch(r"[0-9a-f]{64}", record["sha256"]), "Invalid allowlist record")
    return record


def verify_archive(archive, record, destination):
    require(not destination.exists(), "Destination must be fresh")
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        require(len(members) == 1 and members[0].filename == record["filename"],
                "Staging archive must contain exactly the selected root-level file")
        member = members[0]
        require(not member.is_dir() and not stat.S_ISLNK(member.external_attr >> 16)
                and member.file_size == record["bytes"], "Invalid staged file type/size")
        destination.mkdir(parents=True)
        output = destination / record["filename"]
        try:
            with bundle.open(member) as source, output.open("xb") as target:
                total = 0
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    total += len(chunk)
                    require(total <= record["bytes"], "Staged file exceeded byte limit")
                    target.write(chunk)
            require(total == record["bytes"] and sha(output) == record["sha256"],
                    "File differs from the qualified artifact")
        except BaseException:
            if output.exists():
                output.unlink()
            destination.rmdir()
            raise
    return output


def verify_identity(path, manifest, selection):
    """Check separate packaging-source and original native-build identities."""
    record = manifest["files"][selection]
    if selection == "sdist":
        with tarfile.open(path, "r:gz") as source:
            provenance = json.load(source.extractfile("gmatpy-0.2.0/python/gmatpy/BUILD_PROVENANCE.json"))
            metadata = email.parser.BytesParser().parsebytes(
                source.extractfile("gmatpy-0.2.0/PKG-INFO").read())
    else:
        with zipfile.ZipFile(path) as wheel:
            provenance = json.loads(wheel.read("gmatpy/BUILD_PROVENANCE.json"))
            metadata = email.parser.BytesParser().parsebytes(wheel.read("gmatpy-0.2.0.dist-info/METADATA"))
            reuse = json.loads(wheel.read("gmatpy-0.2.0.dist-info/BINARY_REUSE_PROVENANCE.json"))
            require(reuse["packaging_source_revision"] == SOURCE
                    and reuse["native_build_source_revision"] == NATIVE_SOURCE
                    and reuse["native_recompiled"] is False
                    and reuse["native_build_from_packaging_revision_claimed"] is False
                    and reuse["original_wheel_sha256"] == record["original_qualified_wheel_sha256"],
                    "Binary reuse origin differs")
            require(reuse["native_members_sha256"] == record["native_members_sha256"]
                    and len(record["native_members_sha256"]) == 3,
                    "Native member inventory differs")
            for name, expected in record["native_members_sha256"].items():
                require(hashlib.sha256(wheel.read(name)).hexdigest() == expected,
                        "Native binary differs from qualified original")
    require(metadata["Name"] == manifest["project"] and metadata["Version"] == manifest["version"],
            "Package metadata differs")
    require(all(provenance[key] == manifest["source_receipt"][key] for key in (
        "source_revision", "source_tree_sha256", "working_tree_manifest_sha256")),
        "Packaged source identity differs")


def api_json(path):
    return json.loads(subprocess.check_output(["gh", "api", path], timeout=60))


def retrieve(artifact_id, selection, archive):
    require(re.fullmatch(r"[1-9][0-9]*", artifact_id), "Invalid staging artifact ID")
    base = "repos/" + REPOSITORY + "/actions"
    metadata = api_json(f"{base}/artifacts/{artifact_id}")
    require(metadata["id"] == int(artifact_id) and not metadata["expired"]
            and metadata["name"] == "gmatpy-testpypi-09eafabe-" + selection
            and 0 < metadata["size_in_bytes"] <= SERVICE_CAP,
            "Staging artifact identity/size differs")
    run = api_json(f"{base}/runs/{metadata['workflow_run']['id']}")
    require(run["repository"]["full_name"] == REPOSITORY and run["conclusion"] == "success"
            and run["status"] == "completed" and run["run_attempt"] == 1,
            "Staging run is not a completed first-attempt success in this repository")
    with archive.open("xb") as stream:
        subprocess.run(["gh", "api", f"{base}/artifacts/{artifact_id}/zip"],
                       stdout=stream, check=True, timeout=180)
    require(archive.stat().st_size == metadata["size_in_bytes"]
            and metadata["digest"] == "sha256:" + sha(archive), "Service/archive digest differs")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--selection", choices=SELECTIONS, required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    check_context(os.environ)
    manifest = json.loads(args.manifest.read_text())
    record = check_manifest(manifest, args.selection)
    with tempfile.TemporaryDirectory() as folder:
        archive = Path(folder) / "payload.zip"
        metadata = retrieve(args.artifact_id, args.selection, archive)
        output = verify_archive(archive, record, args.destination)
        verify_identity(output, manifest, args.selection)
    print(json.dumps({"verified_file": output.name, "sha256": sha(output),
                      "bytes": output.stat().st_size, "source_revision": SOURCE,
                      "native_build_source_revision": NATIVE_SOURCE, "native_recompiled": False,
                      "staging_artifact_id": metadata["id"], "index": "TestPyPI"}), flush=True)


if __name__ == "__main__":
    main()
