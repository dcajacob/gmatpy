"""Offline rejection tests; no GitHub, OIDC or package-index calls."""
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import zipfile

import pytest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("guard", ROOT / "verify-testpypi-payload.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def context():
    return {"GITHUB_REPOSITORY": "dcajacob/gmatpy", "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_WORKFLOW_REF": "dcajacob/gmatpy/.github/workflows/publish-testpypi.yml@refs/heads/main"}


def fixture(tmp_path, entries=None):
    data = b"qualified synthetic fixture"
    record = {"filename": "gmatpy-0.2.0.tar.gz", "bytes": len(data),
              "sha256": hashlib.sha256(data).hexdigest()}
    archive = tmp_path / "payload.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        for name, value in entries or [(record["filename"], data)]:
            if name in bundle.namelist():
                with pytest.warns(UserWarning, match="Duplicate name"):
                    bundle.writestr(name, value)
            else:
                bundle.writestr(name, value)
    return archive, record


def test_accepts_exact_file_in_fresh_destination(tmp_path):
    archive, record = fixture(tmp_path)
    output = guard.verify_archive(archive, record, tmp_path / "dist")
    assert guard.sha(output) == record["sha256"]


@pytest.mark.parametrize("key,value", [
    ("GITHUB_REPOSITORY", "other/gmatpy"), ("GITHUB_REF", "refs/heads/other"),
    ("GITHUB_EVENT_NAME", "pull_request"), ("GITHUB_RUN_ATTEMPT", "2"),
    ("GITHUB_WORKFLOW_REF", "dcajacob/gmatpy/.github/workflows/other.yml@refs/heads/main"),
])
def test_rejects_unapproved_workflow_identity(key, value):
    valid = context()
    guard.check_context(valid)
    valid[key] = value
    with pytest.raises(ValueError, match="identity"):
        guard.check_context(valid)


@pytest.mark.parametrize("entries", [
    [("../gmatpy-0.2.0.tar.gz", b"bad")],
    [("gmatpy-0.2.0.tar.gz", b"bad"), ("extra.py", b"bad")],
    [("gmatpy-0.2.0.tar.gz", b"bad"), ("gmatpy-0.2.0.tar.gz", b"bad")],
])
def test_rejects_wrong_paths_extra_or_duplicate_members(tmp_path, entries):
    archive, record = fixture(tmp_path, entries)
    with pytest.raises(ValueError, match="exactly"):
        guard.verify_archive(archive, record, tmp_path / "dist")


def test_rejects_symlink(tmp_path):
    archive, record = fixture(tmp_path)
    with zipfile.ZipFile(archive, "w") as bundle:
        entry = zipfile.ZipInfo(record["filename"])
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        bundle.writestr(entry, b"qualified synthetic fixture")
    with pytest.raises(ValueError, match="type/size"):
        guard.verify_archive(archive, record, tmp_path / "dist")


def test_rejects_tamper_and_removes_failed_output(tmp_path):
    archive, record = fixture(tmp_path)
    record["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="qualified artifact"):
        guard.verify_archive(archive, record, tmp_path / "dist")
    assert not (tmp_path / "dist").exists()


def test_rejects_stale_destination(tmp_path):
    archive, record = fixture(tmp_path)
    (tmp_path / "dist").mkdir()
    with pytest.raises(ValueError, match="fresh"):
        guard.verify_archive(archive, record, tmp_path / "dist")


def test_rejects_unqualified_source():
    manifest = {"schema_version": 1, "project": "gmatpy", "version": "0.2.0",
                "candidate_source_revision": "b52941e9830940c3086839431fd1fb64812076ff"}
    with pytest.raises(ValueError, match="source/project"):
        guard.check_manifest(manifest, "sdist")


def test_retrieval_checks_service_digest(tmp_path, monkeypatch):
    archive, record = fixture(tmp_path)
    metadata = {"id": 123, "expired": False, "name": "gmatpy-testpypi-09eafabe-sdist",
                "size_in_bytes": archive.stat().st_size, "digest": "sha256:" + guard.sha(archive),
                "workflow_run": {"id": 456}}
    run = {"repository": {"full_name": "dcajacob/gmatpy"}, "status": "completed",
           "conclusion": "success", "run_attempt": 1}
    monkeypatch.setattr(guard, "api_json", lambda p: metadata if "/artifacts/" in p else run)

    def fake_download(command, stdout, **kwargs):
        stdout.write(archive.read_bytes())

    monkeypatch.setattr(guard.subprocess, "run", fake_download)
    guard.retrieve("123", "sdist", tmp_path / "valid.zip")
    metadata["digest"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="digest"):
        guard.retrieve("123", "sdist", tmp_path / "invalid.zip")


@pytest.mark.parametrize("artifact_id", ["0", "../other", "123;upload", "12/3"])
def test_rejects_invalid_artifact_id_before_api(artifact_id, tmp_path, monkeypatch):
    monkeypatch.setattr(guard, "api_json", lambda p: pytest.fail("unexpected API call"))
    with pytest.raises(ValueError, match="artifact ID"):
        guard.retrieve(artifact_id, "sdist", tmp_path / "payload.zip")


@pytest.mark.parametrize("change", ["expired", "wrong_name", "oversized", "failed_run", "rerun"])
def test_rejects_unapproved_staging_before_download(change, tmp_path, monkeypatch):
    metadata = {"id": 123, "expired": False, "name": "gmatpy-testpypi-09eafabe-sdist",
                "size_in_bytes": 100, "workflow_run": {"id": 456}}
    run = {"repository": {"full_name": "dcajacob/gmatpy"}, "status": "completed",
           "conclusion": "success", "run_attempt": 1}
    if change == "expired":
        metadata["expired"] = True
    elif change == "wrong_name":
        metadata["name"] = "unreviewed-payload"
    elif change == "oversized":
        metadata["size_in_bytes"] = guard.SERVICE_CAP + 1
    elif change == "failed_run":
        run["conclusion"] = "failure"
    else:
        run["run_attempt"] = 2
    monkeypatch.setattr(guard, "api_json", lambda p: metadata if "/artifacts/" in p else run)
    monkeypatch.setattr(guard.subprocess, "run", lambda *a, **k: pytest.fail("unexpected download"))
    with pytest.raises(ValueError):
        guard.retrieve("123", "sdist", tmp_path / "payload.zip")


def identity_fixture(tmp_path, change=None):
    native = {f"gmatpy/_native/library{i}.so": bytes([i]) for i in range(3)}
    native_hashes = {n: hashlib.sha256(b).hexdigest() for n, b in native.items()}
    source = {"source_revision": guard.SOURCE, "source_tree_sha256": "1" * 64,
              "working_tree_manifest_sha256": "2" * 64}
    reuse = {"packaging_source_revision": guard.SOURCE,
             "native_build_source_revision": guard.NATIVE_SOURCE,
             "native_recompiled": False, "native_build_from_packaging_revision_claimed": False,
             "original_wheel_sha256": "3" * 64, "native_members_sha256": native_hashes}
    if change == "native_source":
        reuse["native_build_source_revision"] = guard.SOURCE
    elif change == "compilation_claim":
        reuse["native_recompiled"] = True
    elif change == "packaging_source":
        reuse["packaging_source_revision"] = guard.NATIVE_SOURCE
    elif change == "native_bytes":
        native[next(iter(native))] = b"changed"
    wheel = tmp_path / "fixture.whl"
    with zipfile.ZipFile(wheel, "w") as z:
        for n, data in native.items():
            z.writestr(n, data)
        z.writestr("gmatpy/BUILD_PROVENANCE.json", json.dumps(source))
        z.writestr("gmatpy-0.2.0.dist-info/METADATA", "Name: gmatpy\nVersion: 0.2.0\n")
        z.writestr("gmatpy-0.2.0.dist-info/BINARY_REUSE_PROVENANCE.json", json.dumps(reuse))
    manifest = {"project": "gmatpy", "version": "0.2.0", "source_receipt": source,
                "files": {"linux-x86_64": {"native_members_sha256": native_hashes,
                                           "original_qualified_wheel_sha256": "3" * 64}}}
    if change == "source_inventory":
        manifest["source_receipt"] = dict(source, source_tree_sha256="0" * 64)
    return wheel, manifest


def test_accepts_explicit_separate_native_and_packaging_origins(tmp_path):
    wheel, manifest = identity_fixture(tmp_path)
    guard.verify_identity(wheel, manifest, "linux-x86_64")


@pytest.mark.parametrize("change", ["native_source", "compilation_claim", "packaging_source",
                                     "native_bytes", "source_inventory"])
def test_rejects_false_binary_reuse_or_source_identity(change, tmp_path):
    wheel, manifest = identity_fixture(tmp_path, change)
    with pytest.raises(ValueError):
        guard.verify_identity(wheel, manifest, "linux-x86_64")
