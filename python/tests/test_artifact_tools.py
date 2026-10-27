"""Artifact identity and archive validation; no installed engine required."""

import io
import hashlib
import json
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
from check_distribution import check, export_scope_digest, export_scope_files
from record_source import record, source_digest


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
    data = []
    for index in range(17):
        name = ("planetary_ephem/spk/kernel.bsp" if index == 0 else
                f"time/generated-{index:02d}.dat")
        contents = f"synthetic data {index}\n".encode()
        result["application/data/" + name] = contents
        data.append({"path": name, "status": "documented_reuse_basis",
                     "sha256": hashlib.sha256(contents).hexdigest()})
    result[package + "licenses/DATA_MANIFEST.json"] = json.dumps({
        "schema_version": 1, "files": data}).encode()
    result[package + "__init__.py"] = b"value = 1\n"
    result["PKG-INFO"] = b"Name: gmatpy\nVersion: 0.2.0\n"
    return result


def _sdist(path, files, duplicate=None):
    with tarfile.open(path, "w:gz") as archive:
        for name, contents in list(files.items()) + ([duplicate] if duplicate else []):
            info = tarfile.TarInfo("gmatpy-0.2.0/" + name)
            info.size, info.mode = len(contents), 0o644
            archive.addfile(info, io.BytesIO(contents))


def _candidate(tmp_path, files=None):
    files = _files() if files is None else files
    artifact = tmp_path / "source.tar.gz"
    _sdist(artifact, files)
    manifest = json.dumps(record(artifact, "a" * 40, "b" * 64)).encode()
    files["python/gmatpy/BUILD_PROVENANCE.json"] = manifest
    manifest_path = tmp_path / "source.json"
    manifest_path.write_bytes(manifest)
    _sdist(artifact, files)
    return artifact, manifest_path, files


def _export_candidate(tmp_path):
    files = _files()
    source = tmp_path / "scope-source.tar.gz"
    _sdist(source, files)
    determination = {
        "schema_version": 1, "status": "owner_adopted",
        "package": {"name": "gmatpy", "version": "0.2.0"},
        "scope": {"selection": "gmatpy-scientific-payload-v1",
                  "sha256": export_scope_digest(record(source, "a" * 40, "b" * 64)["files"])},
    }
    code = json.loads(files["python/gmatpy/licenses/CODE_MANIFEST.json"])
    code["publication_review"] = [{
        "id": "cspice-derived-export-designation", "status": "resolved",
        "determination_file": "EXPORT_DETERMINATION.json", "notes": "adopted",
    }]
    files["python/gmatpy/licenses/CODE_MANIFEST.json"] = json.dumps(code).encode()
    _export_record(files, determination)
    return _candidate(tmp_path, files)


def _export_record(files, determination):
    contents = json.dumps(determination).encode()
    files["python/gmatpy/licenses/EXPORT_DETERMINATION.json"] = contents
    code = json.loads(files["python/gmatpy/licenses/CODE_MANIFEST.json"])
    code["publication_review"][0]["determination_sha256"] = hashlib.sha256(contents).hexdigest()
    files["python/gmatpy/licenses/CODE_MANIFEST.json"] = json.dumps(code).encode()


def _wheel(path, files, *, profile=None, build=None, tag="cp314-cp314-linux_x86_64",
           omit=()):
    profile = profile if profile is not None else {
        "schema_version": 1, "profile": "extended", "spice": True,
        "data_files": [name.removeprefix("application/data/") for name in files
                       if name.startswith("application/data/")],
    }
    wheel_files = {}
    for name, contents in files.items():
        if name.startswith("python/gmatpy/"):
            wheel_files[name[len("python/"):]] = contents
        elif name.startswith("application/data/"):
            wheel_files["gmatpy/data/" + name[len("application/data/"):]] = contents
    wheel_files["gmatpy/BUILD_PROFILE.json"] = json.dumps(profile).encode()
    wheel_files["gmatpy-0.2.0.dist-info/METADATA"] = files["PKG-INFO"]
    wheel_files["gmatpy-0.2.0.dist-info/WHEEL"] = (
        "Wheel-Version: 1.0\nRoot-Is-Purelib: false\n" +
        (f"Build: {build}\n" if build is not None else "") + f"Tag: {tag}\n").encode()
    with zipfile.ZipFile(path, "w") as archive:
        for name, contents in wheel_files.items():
            if name not in omit:
                archive.writestr(name, contents)


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
        artifact = tmp_path / "gmatpy-0.2.0-cp314-cp314-linux_x86_64.whl"
        contents = dict(files)
        if tamper:
            contents["python/gmatpy/__init__.py"] = b"changed"
        _wheel(artifact, contents)
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


@pytest.mark.parametrize("profile,spice,message", [
    ("minimal", False, "Only the standard full headless build"),
    ("minimal", True, "Only the standard full headless build"),
    ("extended", False, "must include SPICE"),
    ("extended", 1, "must include SPICE"),
])
def test_wheel_requires_full_build_metadata(tmp_path, profile, spice, message):
    artifact = tmp_path / "gmatpy-0.2.0-cp314-cp314-linux_x86_64.whl"
    _wheel(artifact, _files(), profile={
        "schema_version": 1, "profile": profile, "spice": spice, "data_files": []})
    with pytest.raises(ValueError, match=message):
        check(artifact)


@pytest.mark.parametrize("tag", ["1minimal", "2extended", "3"])
@pytest.mark.parametrize("location", ["filename", "metadata"])
def test_wheel_rejects_variant_build_tags(tmp_path, tag, location):
    prefix = f"gmatpy-0.2.0-{tag}" if location == "filename" else "gmatpy-0.2.0"
    artifact = tmp_path / f"{prefix}-cp314-cp314-linux_x86_64.whl"
    _wheel(artifact, _files(), build=tag if location == "metadata" else None)
    with pytest.raises(ValueError, match="[Bb]uild tag"):
        check(artifact)


@pytest.mark.parametrize("missing,message", [
    ("gmatpy/BUILD_PROFILE.json", "missing required BUILD_PROFILE"),
    ("gmatpy-0.2.0.dist-info/WHEEL", "exactly one matching WHEEL"),
])
def test_wheel_requires_profile_and_wheel_metadata(tmp_path, missing, message):
    artifact = tmp_path / "gmatpy-0.2.0-cp314-cp314-linux_x86_64.whl"
    _wheel(artifact, _files(), omit=(missing,))
    with pytest.raises(ValueError, match=message):
        check(artifact)


def test_wheel_rejects_compatibility_tag_laundering(tmp_path):
    artifact = tmp_path / "gmatpy-0.2.0-cp314-cp314-linux_x86_64.whl"
    _wheel(artifact, _files(), tag="cp313-cp313-linux_x86_64")
    with pytest.raises(ValueError, match="compatibility tags differ"):
        check(artifact)


def test_wheel_cannot_drop_spice_from_profile_and_inventory(tmp_path):
    files = _files()
    selected = [name.removeprefix("application/data/") for name in files
                if name.startswith("application/data/") and not name.endswith("kernel.bsp")]
    artifact = tmp_path / "gmatpy-0.2.0-cp314-cp314-linux_x86_64.whl"
    _wheel(artifact, files, profile={"schema_version": 1, "profile": "extended",
                                   "spice": True, "data_files": selected},
           omit=("gmatpy/data/planetary_ephem/spk/kernel.bsp",))
    with pytest.raises(ValueError, match="unexpected data selection"):
        check(artifact)


def test_wheel_requires_current_complete_17_file_data_manifest(tmp_path):
    files = _files()
    del files["application/data/planetary_ephem/spk/kernel.bsp"]
    manifest = json.loads(files["python/gmatpy/licenses/DATA_MANIFEST.json"])
    manifest["files"] = [record for record in manifest["files"]
                         if not record["path"].endswith("kernel.bsp")]
    files["python/gmatpy/licenses/DATA_MANIFEST.json"] = json.dumps(manifest).encode()
    artifact = tmp_path / "gmatpy-0.2.0-cp314-cp314-linux_x86_64.whl"
    _wheel(artifact, files)
    with pytest.raises(ValueError, match="all 17 packaged data files"):
        check(artifact)


@pytest.mark.skipif(os.name == "nt", reason="Unix build_wheel.sh helper; Windows uses the native qualification driver")
@pytest.mark.parametrize("profile", ["minimal", "unknown", ""])
def test_build_helper_rejects_obsolete_profile_before_build(tmp_path, profile):
    environment = dict(os.environ, GMAT_PY_PROFILE=profile,
                       GMAT_PY_PYTHON="must-not-run-a-build",
                       GMAT_PY_WHEEL_DIR=str(tmp_path / "uncreated"))
    environment.pop("CSPICE_DIR", None)
    result = subprocess.run(["bash", str(TOOLS / "build_wheel.sh")],
                            env=environment, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert "is obsolete" in result.stderr
    assert not (tmp_path / "uncreated").exists()


@pytest.mark.skipif(os.name == "nt", reason="Unix build_wheel.sh helper; Windows uses the native qualification driver")
@pytest.mark.parametrize("profile", [None, "extended"])
def test_build_helper_accepts_unset_or_full_profile_before_dependency_check(tmp_path, profile):
    environment = dict(os.environ, GMAT_PY_PYTHON="must-not-run-a-build",
                       GMAT_PY_WHEEL_DIR=str(tmp_path / "uncreated"))
    environment.pop("GMAT_PY_PROFILE", None)
    environment.pop("CSPICE_DIR", None)
    if profile is not None:
        environment["GMAT_PY_PROFILE"] = profile
    result = subprocess.run(["bash", str(TOOLS / "build_wheel.sh")],
                            env=environment, capture_output=True, text=True, timeout=10)
    assert result.returncode == 1
    assert "Set CSPICE_DIR" in result.stderr
    assert "is obsolete" not in result.stderr
    assert not (tmp_path / "uncreated").exists()


def test_qualification_rejects_obsolete_profile_before_build(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "qualification", TOOLS.parent / "ci" / "qualify.py")
    qualification = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qualification)
    monkeypatch.setenv("GMAT_PY_PROFILE", "minimal")
    with pytest.raises(ValueError, match="GMAT_PY_PROFILE is obsolete"):
        qualification.qualify(None)


def test_export_scope_selection_is_exact_sorted_and_preserves_complete_records():
    included = ["src/base/engine.cpp", "swig/api.i", "application/data/ephemeris.bin",
                "build/toolchain.cmake", "depends/library/source.c", "CMakeLists.txt",
                "pyproject.toml", "python/CMakeLists.txt", "python/ci/build_cspice.py",
                "python/ci/cspice-sources.json", "python/gmatpy/__init__.py",
                "python/gmatpy/_native/__init__.py"]
    excluded = ["src-other/file.cpp", "swig-other/file.i", "README.md", "docs/index.rst",
                "python/tests/test_artifact_tools.py", "python/tools/check_distribution.py",
                "python/ci/qualify.py", "python/gmatpy/NOTICE.txt", "python/gmatpy/LICENSES.md",
                "python/gmatpy/BUILD_PROVENANCE.json", "python/gmatpy/BUILD_PROFILE.json",
                "python/gmatpy/licenses/CODE_MANIFEST.json",
                "python/gmatpy/licenses/EXPORT_DETERMINATION.json"]
    records = [{"path": name, "mode": 0o644, "size": 1, "sha256": "a" * 64}
               for name in reversed(included + excluded)]
    selected = export_scope_files(records)
    assert [item["path"] for item in selected] == sorted(included)
    assert export_scope_digest(records) == source_digest(selected)
    for field, value in [("mode", 0o755), ("size", 2), ("sha256", "b" * 64),
                         ("path", "src/base/changed.cpp")]:
        changed = [dict(item) for item in selected]
        changed[0][field] = value
        assert export_scope_digest(changed) != export_scope_digest(selected)


@pytest.mark.parametrize("kind", ["sdist", "wheel"])
@pytest.mark.parametrize("external_manifest", [False, True])
def test_resolved_export_record_proves_scope(tmp_path, kind, external_manifest):
    artifact, manifest, files = _export_candidate(tmp_path)
    if kind == "wheel":
        artifact = tmp_path / "gmatpy-0.2.0-cp314-cp314-linux_x86_64.whl"
        _wheel(artifact, files)
    assert check(artifact, release=True,
                 source_manifest=manifest if external_manifest else None) == []


def test_resolved_export_requires_included_determination_record(tmp_path):
    _, _, files = _export_candidate(tmp_path)
    del files["python/gmatpy/licenses/EXPORT_DETERMINATION.json"]
    artifact, _, _ = _candidate(tmp_path, files)
    with pytest.raises(ValueError, match="Required distribution file missing: .*EXPORT_DETERMINATION.json"):
        check(artifact, release=True)


def test_resolved_export_rejects_record_hash_tamper(tmp_path):
    _, _, files = _export_candidate(tmp_path)
    files["python/gmatpy/licenses/EXPORT_DETERMINATION.json"] += b"\n"
    artifact, _, _ = _candidate(tmp_path, files)
    with pytest.raises(ValueError, match="Export determination hash mismatch"):
        check(artifact, release=True)


@pytest.mark.parametrize("field,value,message", [
    ("schema_version", 2, "not an adopted schema-1 record"),
    ("status", "draft", "not an adopted schema-1 record"),
    ("package", {"name": "gmatpy", "version": "0.3.0"}, "package differs"),
    ("scope", {"selection": "other", "sha256": "a" * 64}, "Unsupported export determination scope"),
    ("scope", {"selection": "gmatpy-scientific-payload-v1", "sha256": "a" * 64},
     "scope differs from scientific payload"),
])
def test_resolved_export_rejects_wrong_adoption_or_scope(tmp_path, field, value, message):
    _, _, files = _export_candidate(tmp_path)
    determination = json.loads(files["python/gmatpy/licenses/EXPORT_DETERMINATION.json"])
    determination[field] = value
    _export_record(files, determination)
    artifact, _, _ = _candidate(tmp_path, files)
    with pytest.raises(ValueError, match=message):
        check(artifact, release=True)


def test_resolved_export_requires_exact_record_filename(tmp_path):
    _, _, files = _export_candidate(tmp_path)
    code = json.loads(files["python/gmatpy/licenses/CODE_MANIFEST.json"])
    code["publication_review"][0]["determination_file"] = "another.json"
    files["python/gmatpy/licenses/CODE_MANIFEST.json"] = json.dumps(code).encode()
    artifact, _, _ = _candidate(tmp_path, files)
    with pytest.raises(ValueError, match="requires EXPORT_DETERMINATION.json"):
        check(artifact, release=True)


def test_resolved_export_rejects_changed_science_with_fresh_provenance(tmp_path):
    _, _, files = _export_candidate(tmp_path)
    files["python/gmatpy/__init__.py"] = b"changed scientific facade\n"
    artifact, _, _ = _candidate(tmp_path, files)
    with pytest.raises(ValueError, match="scope differs from scientific payload"):
        check(artifact, release=True)


def test_resolved_export_independently_validates_embedded_provenance(tmp_path):
    artifact, _, files = _export_candidate(tmp_path)
    provenance = json.loads(files["python/gmatpy/BUILD_PROVENANCE.json"])
    provenance["source_tree_sha256"] = "a" * 64
    files["python/gmatpy/BUILD_PROVENANCE.json"] = json.dumps(provenance).encode()
    _sdist(artifact, files)
    with pytest.raises(ValueError, match="Source provenance digest mismatch"):
        check(artifact, release=True)


@pytest.mark.parametrize("kind,message", [
    ("sdist", "Source archive differs from candidate source manifest"),
    ("wheel", "Wheel/source hash mismatch"),
])
def test_resolved_export_rejects_payload_tamper_without_external_manifest(tmp_path, kind, message):
    artifact, _, files = _export_candidate(tmp_path)
    files["python/gmatpy/__init__.py"] = b"tampered facade\n"
    if kind == "sdist":
        _sdist(artifact, files)
    else:
        artifact = tmp_path / "gmatpy-0.2.0-cp314-cp314-linux_x86_64.whl"
        _wheel(artifact, files)
    with pytest.raises(ValueError, match=message):
        check(artifact, release=True)


@pytest.mark.parametrize("external_manifest", [False, True])
@pytest.mark.parametrize("name", ["gmatpy/unrecorded_science.py", "gmatpy/_native/unrecorded.py",
                                  "gmatpy/_native/libGmatBase.so.unrecorded.py"])
def test_resolved_export_rejects_unrecorded_wheel_payload(tmp_path, external_manifest, name):
    _, manifest, files = _export_candidate(tmp_path)
    artifact = tmp_path / "gmatpy-0.2.0-cp314-cp314-linux_x86_64.whl"
    _wheel(artifact, files)
    with zipfile.ZipFile(artifact, "a") as archive:
        archive.writestr(name, b"unrecorded scientific behavior\n")
    with pytest.raises(ValueError, match="Unrecorded wheel package payload"):
        check(artifact, release=True,
              source_manifest=manifest if external_manifest else None)


@pytest.mark.parametrize("suffix", [".so.R2026a", ".dylib", ".R2026a.dylib", ".dll"])
def test_resolved_export_allows_known_generated_native_outputs(tmp_path, suffix):
    _, manifest, files = _export_candidate(tmp_path)
    artifact = tmp_path / "gmatpy-0.2.0-cp314-cp314-linux_x86_64.whl"
    _wheel(artifact, files)
    with zipfile.ZipFile(artifact, "a") as archive:
        for name in ["_gmat_py.pyd" if suffix == ".dll" else "_gmat_py.so", "gmat_py.py",
                     "libGmatBase" + suffix, "libGmatUtil" + suffix]:
            archive.writestr("gmatpy/_native/" + name, b"synthetic generated file\n")
    assert check(artifact, release=True, source_manifest=manifest) == []
