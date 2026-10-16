"""Artifact identity and archive validation; no installed engine required."""

import io
import json
from pathlib import Path
import sys
import tarfile
import zipfile

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
from check_distribution import check
from record_source import record


def _files():
    package = "python/gmatpy/"
    result = {package + name: b"notice" for name in (
        "NOTICE.txt", "LICENSES.md", "licenses/NAIF-CSPICE.txt",
        "licenses/F2C.txt", "licenses/SWIG.txt")}
    result[package + "licenses/GMAT.txt"] = b"Apache License Version 2.0"
    result["application/License.txt"] = result[package + "licenses/GMAT.txt"]
    result[package + "licenses/CODE_MANIFEST.json"] = json.dumps({
        "schema_version": 1, "package": {"name": "gmatpy", "version": "0.2.0"},
        "components": [], "publication_review": [{"id": "owner", "status": "pending", "notes": "decision needed"}],
    }).encode()
    result[package + "licenses/DATA_MANIFEST.json"] = b'{"schema_version":1,"files":[]}'
    result[package + "__init__.py"] = b"value = 1\n"
    result["PKG-INFO"] = b"Name: gmatpy\nVersion: 0.2.0\n"
    return result


def _sdist(path, files, duplicate=None):
    with tarfile.open(path, "w:gz") as archive:
        for name, contents in list(files.items()) + ([duplicate] if duplicate else []):
            info = tarfile.TarInfo("gmatpy-0.2.0/" + name)
            info.size, info.mode = len(contents), 0o644
            archive.addfile(info, io.BytesIO(contents))


def _candidate(tmp_path):
    files = _files()
    artifact = tmp_path / "source.tar.gz"
    _sdist(artifact, files)
    manifest = json.dumps(record(artifact, "a" * 40, "b" * 64)).encode()
    files["python/gmatpy/BUILD_PROVENANCE.json"] = manifest
    manifest_path = tmp_path / "source.json"
    manifest_path.write_bytes(manifest)
    _sdist(artifact, files)
    return artifact, manifest_path, files


def test_sdist_identity_and_release_hold(tmp_path):
    artifact, manifest, _ = _candidate(tmp_path)
    assert check(artifact, source_manifest=manifest) == ["owner: decision needed"]
    with pytest.raises(ValueError, match="Release review unresolved"):
        check(artifact, release=True, source_manifest=manifest)


def test_changed_source_fails_candidate_identity(tmp_path):
    artifact, manifest, files = _candidate(tmp_path)
    files["python/gmatpy/__init__.py"] = b"value = 2\n"
    _sdist(artifact, files)
    with pytest.raises(ValueError, match="differs from candidate source manifest"):
        check(artifact, source_manifest=manifest)


def test_wheel_matches_copied_sources_and_rejects_tamper(tmp_path):
    _, manifest, files = _candidate(tmp_path)
    for tamper in (False, True):
        artifact = tmp_path / "candidate.whl"
        with zipfile.ZipFile(artifact, "w") as archive:
            for name, contents in files.items():
                if name.startswith("python/gmatpy/"):
                    archive.writestr(name[len("python/"):], b"changed" if tamper and name.endswith("__init__.py") else contents)
            archive.writestr("gmatpy-0.2.0.dist-info/METADATA", files["PKG-INFO"])
        if tamper:
            with pytest.raises(ValueError, match="Wheel/source hash mismatch"):
                check(artifact, source_manifest=manifest)
        else:
            check(artifact, source_manifest=manifest)


def test_duplicate_archive_member_rejected(tmp_path):
    artifact = tmp_path / "source.tar.gz"
    _sdist(artifact, _files(), ("PKG-INFO", b"Name: other\n"))
    with pytest.raises(ValueError, match="Duplicate archive member"):
        check(artifact)


@pytest.mark.parametrize("name", ["../escape", "/absolute"])
def test_unsafe_source_path_rejected(tmp_path, name):
    artifact = tmp_path / "source.tar.gz"
    _sdist(artifact, {name: b"content"})
    with pytest.raises(ValueError, match="Unsafe"):
        record(artifact, "a" * 40, "b" * 64)


def test_metadata_mismatch_rejected(tmp_path):
    files = _files()
    files["PKG-INFO"] = b"Name: wrong\nVersion: 0.2.0\n"
    artifact = tmp_path / "source.tar.gz"
    _sdist(artifact, files)
    with pytest.raises(ValueError, match="Package Name differs"):
        check(artifact)


def test_profile_metadata_cannot_claim_a_partial_arbitrary_inventory(tmp_path):
    _, manifest, files = _candidate(tmp_path)
    artifact = tmp_path/'minimal.whl'
    with zipfile.ZipFile(artifact,'w') as archive:
        for name, contents in files.items():
            if name.startswith('python/gmatpy/'):
                archive.writestr(name[len('python/'):],contents)
        archive.writestr('gmatpy-0.2.0.dist-info/METADATA',files['PKG-INFO'])
        archive.writestr('gmatpy/BUILD_PROFILE.json',json.dumps({
            'schema_version':1,'profile':'minimal','spice':True,'data_files':[]}))
    with pytest.raises(ValueError,match='SPICE configuration mismatch'):
        check(artifact,source_manifest=manifest)
