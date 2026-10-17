"""Read one approved draft asset and stage its exact allowlisted bytes for TestPyPI."""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess

spec = importlib.util.spec_from_file_location(
    "payload_guard", Path(__file__).with_name("verify-testpypi-payload.py"))
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
TAG = "testpypi-staging-09eafabe"


def check_context(environment):
    expected = {
        "GITHUB_REPOSITORY": guard.REPOSITORY,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_WORKFLOW_REF": guard.REPOSITORY + "/.github/workflows/stage-testpypi.yml@refs/heads/main",
    }
    guard.require(all(environment.get(k) == v for k, v in expected.items()),
                  "Unapproved staging workflow identity")


def check_release(release, release_id, asset_id, record):
    guard.require(re.fullmatch(r"[1-9][0-9]*", release_id)
                  and re.fullmatch(r"[1-9][0-9]*", asset_id), "Invalid release/asset ID")
    guard.require(release["id"] == int(release_id) and release["draft"] is True
                  and release["tag_name"] == TAG
                  and release["target_commitish"] == guard.SOURCE
                  and release["author"]["login"] == "dcajacob",
                  "Unapproved staging draft")
    assets = release["assets"]
    guard.require(len(assets) == 1, "Draft must contain exactly one selected asset")
    asset = assets[0]
    guard.require(asset["id"] == int(asset_id) and asset["name"] == record["filename"]
                  and asset["size"] == record["bytes"] and asset["state"] == "uploaded"
                  and asset["digest"] == "sha256:" + record["sha256"]
                  and asset["uploader"]["login"] == "dcajacob",
                  "Draft asset differs from allowlisted candidate")


def main():
    check_context(os.environ)
    selection = os.environ["PAYLOAD_SELECTION"]
    manifest = json.loads(Path(".github/release/testpypi-09eafabe.json").read_text())
    record = guard.check_manifest(manifest, selection)
    release_id = os.environ["DRAFT_RELEASE_ID"]
    asset_id = os.environ["DRAFT_ASSET_ID"]
    guard.require(re.fullmatch(r"[1-9][0-9]*", release_id)
                  and re.fullmatch(r"[1-9][0-9]*", asset_id), "Invalid release/asset ID")
    base = "repos/" + guard.REPOSITORY + "/releases"
    release = guard.api_json(f"{base}/{release_id}")
    check_release(release, release_id, asset_id, record)
    destination = Path("stage")
    destination.mkdir(exist_ok=False)
    output = destination / record["filename"]
    try:
        with output.open("xb") as target:
            subprocess.run(["gh", "api", "-H", "Accept: application/octet-stream",
                            f"{base}/assets/{asset_id}"], stdout=target, check=True, timeout=180)
        guard.require(output.stat().st_size == record["bytes"]
                      and guard.sha(output) == record["sha256"],
                      "Downloaded draft asset bytes differ")
        guard.verify_identity(output, manifest, selection)
        # Fail if the draft was published or its inventory changed during retrieval.
        check_release(guard.api_json(f"{base}/{release_id}"), release_id, asset_id, record)
    except BaseException:
        output.unlink(missing_ok=True)
        destination.rmdir()
        raise
    print(json.dumps({"verified_file": output.name, "bytes": output.stat().st_size,
                      "sha256": guard.sha(output), "draft_release_id": int(release_id),
                      "draft_asset_id": int(asset_id), "source_revision": guard.SOURCE,
                      "native_build_source_revision": guard.NATIVE_SOURCE,
                      "native_recompiled": False}), flush=True)


if __name__ == "__main__":
    main()
