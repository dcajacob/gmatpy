"""Prepare only the five unchanged TestPyPI-qualified distributions for PyPI."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

spec = importlib.util.spec_from_file_location(
    "guard", Path(__file__).with_name("verify-testpypi-payload.py"))
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
BASE_SHA256 = "e337947850811068988f4bbdfa361dce439a6bc330796d10f741c5f5ca101316"
TRIAL_SHA256 = "d9e19209efc343646f43edd160f5645661c5a67abe603f73ddcc7a47ca3dd451"
ORDER = ("linux-x86_64", "linux-arm64", "macos-arm64", "macos-x86_64", "sdist")


def check_context(environment):
    expected = {
        "GITHUB_REPOSITORY": guard.REPOSITORY,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_WORKFLOW_REF": guard.REPOSITORY + "/.github/workflows/publish-pypi.yml@refs/heads/main",
    }
    guard.require(all(environment.get(key) == value for key, value in expected.items()),
                  "Unapproved production workflow identity")


def check_url(url, filename):
    parsed = urllib.parse.urlsplit(url)
    guard.require(parsed.scheme == "https" and parsed.netloc == "test-files.pythonhosted.org"
                  and not parsed.query and not parsed.fragment
                  and re.fullmatch(r"/packages/[0-9a-f]{2}/[0-9a-f]{2}/[0-9a-f]+/"
                                   + re.escape(filename), parsed.path),
                  "Unapproved public download URL")


def check_config(config, base_bytes):
    guard.require(config["schema_version"] == 1 and config["project"] == "gmatpy"
                  and config["version"] == "0.2.0"
                  and config["upload_endpoint"] == "https://upload.pypi.org/legacy/"
                  and config["base_allowlist_sha256"] == BASE_SHA256
                  and hashlib.sha256(base_bytes).hexdigest() == BASE_SHA256
                  and config["testpypi_trial_receipt_sha256"] == TRIAL_SHA256,
                  "Promotion differs from the fixed TestPyPI trial")
    manifest = json.loads(base_bytes)
    guard.require(set(config["public_testpypi_downloads"]) == set(ORDER),
                  "Promotion must contain exactly all five files")
    for selection in ORDER:
        record = guard.check_manifest(manifest, selection)
        check_url(config["public_testpypi_downloads"][selection], record["filename"])
    return manifest


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Unexpected public download redirect")


def require_new_project(opener):
    request = urllib.request.Request("https://pypi.org/pypi/gmatpy/json",
                                     headers={"Cache-Control": "no-cache"})
    try:
        with opener.open(request, timeout=30):
            raise ValueError("Production project exists; stop for owner review")
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise


def download_one(opener, url, output, record):
    check_url(url, record["filename"])
    created = False
    try:
        with opener.open(url, timeout=60) as response, output.open("xb") as target:
            created = True
            guard.require(response.status == 200
                          and response.headers.get("Content-Encoding", "identity") == "identity",
                          "Unexpected download response")
            digest, total = hashlib.sha256(), 0
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                total += len(chunk)
                guard.require(total <= record["bytes"], "Download exceeded the fixed byte limit")
                digest.update(chunk)
                target.write(chunk)
        guard.require(total == record["bytes"] and digest.hexdigest() == record["sha256"],
                      "Downloaded distribution differs from the qualified file")
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise


def prepare(config, manifest, destination):
    destination.mkdir(exist_ok=False)
    opener = urllib.request.build_opener(NoRedirect())
    outputs = []
    try:
        for selection in ORDER:
            record = manifest["files"][selection]
            output = destination / record["filename"]
            download_one(opener, config["public_testpypi_downloads"][selection], output, record)
            outputs.append(output)
            guard.verify_identity(output, manifest, selection)
        guard.require({p.name for p in destination.iterdir()}
                      == {r["filename"] for r in manifest["files"].values()},
                      "Unexpected file in publishing directory")
    except BaseException:
        for output in outputs:
            output.unlink(missing_ok=True)
        destination.rmdir()
        raise
    print(json.dumps({"project": "gmatpy", "version": "0.2.0", "files": [
        {"filename": path.name, "bytes": path.stat().st_size, "sha256": guard.sha(path)}
        for path in outputs], "packaging_revision": guard.SOURCE,
        "native_revision": guard.NATIVE_SOURCE, "native_recompiled": False,
        "upload_endpoint": config["upload_endpoint"]}), flush=True)


def main():
    check_context(os.environ)
    config = json.loads(Path(".github/release/pypi-0.2.0.json").read_text())
    manifest = check_config(config, Path(".github/release/testpypi-09eafabe.json").read_bytes())
    opener = urllib.request.build_opener(NoRedirect())
    require_new_project(opener)
    prepare(config, manifest, Path("dist"))
    # Refuse a conflicting project that appeared while retrieving the files.
    require_new_project(opener)


if __name__ == "__main__":
    main()
