"""Verify GMAT Py artifact notices, data inventory and release-review status.

Run with a wheel or source archive. --release additionally rejects unresolved
manifest review items. It is a release preflight, not a legal determination.
"""

import argparse
from contextlib import contextmanager
from email.parser import BytesParser
import hashlib
from itertools import product
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import zipfile

from record_source import PROVENANCE, source_digest, source_files


def unique_names(raw_names):
    names = list(raw_names)
    if len(names) != len(set(names)):
        raise ValueError("Duplicate archive member")
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or str(path) != name.rstrip("/"):
            raise ValueError(f"Unsafe archive path: {name}")


@contextmanager
def archive_files(path):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            unique_names(archive.namelist())
            names = {name: name for name in archive.namelist() if not name.endswith("/")}
            yield names, archive.open, "gmatpy", "gmatpy/data/"
    else:
        with tarfile.open(path, "r:gz") as archive:
            unique_names(member.name for member in archive.getmembers())
            if any(not member.isfile() and not member.isdir() for member in archive.getmembers()):
                raise ValueError("Source archive must not contain links or special files")
            members = [member for member in archive.getmembers() if member.isfile()]
            roots = {member.name.split("/", 1)[0] for member in members}
            if len(roots) != 1:
                raise ValueError("Source archive must have a single top-level directory")
            names = {member.name.split("/", 1)[1]: member for member in members}
            yield names, archive.extractfile, "python/gmatpy", "application/data/"


def check(path, *, release=False, source_manifest=None):
    with archive_files(path) as (names, open_member, package, data_prefix):
        is_wheel = package == "gmatpy"
        profile = None
        profile_name = f"{package}/BUILD_PROFILE.json"
        if profile_name in names:
            with open_member(names[profile_name]) as stream:
                profile = json.loads(stream.read())
            if profile.get("schema_version") != 1 or profile.get("profile") != "extended":
                raise ValueError("Only the standard full headless build is supported (internal profile: extended)")
            if profile.get("spice") is not True:
                raise ValueError("Standard full headless build must include SPICE")
        elif is_wheel:
            raise ValueError("Wheel is missing required BUILD_PROFILE.json")
        def read(name):
            if name not in names:
                raise ValueError(f"Required distribution file missing: {name}")
            with open_member(names[name]) as stream:
                return stream.read()

        required = ("NOTICE.txt", "LICENSES.md", "licenses/GMAT.txt",
                    "licenses/NAIF-CSPICE.txt", "licenses/F2C.txt",
                    "licenses/SWIG.txt", "licenses/CODE_MANIFEST.json",
                    "licenses/DATA_MANIFEST.json")
        for relative in required:
            if not read(f"{package}/{relative}").strip():
                raise ValueError(f"Empty distribution notice: {relative}")
        apache = read(f"{package}/licenses/GMAT.txt")
        if b"Apache License" not in apache or b"Version 2.0" not in apache:
            raise ValueError("GMAT license is not the Apache 2.0 text")
        code = json.loads(read(f"{package}/licenses/CODE_MANIFEST.json"))
        if code.get("schema_version") != 1:
            raise ValueError("Unsupported code-manifest schema")
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if package.startswith("python/"):
            metadata_name = "PKG-INFO"
        else:
            if len(metadata_names) != 1:
                raise ValueError("Wheel must contain exactly one package METADATA")
            metadata_name = metadata_names[0]
        metadata = BytesParser().parsebytes(read(metadata_name))
        for field in ("Name", "Version"):
            if metadata[field] != code["package"][field.lower()]:
                raise ValueError(f"Package {field} differs from code manifest")
        if is_wheel:
            # A wheel build number cannot select a different installed feature
            # set. The one published package uses ordinary, untagged filenames.
            filename = Path(path).name
            parts = filename.removesuffix(".whl").split("-")
            if not filename.endswith(".whl") or len(parts) != 5:
                raise ValueError("Standard wheel filename must not contain a build tag")
            distribution, version, python_tag, abi_tag, platform_tag = parts
            if distribution != metadata["Name"].replace("-", "_") or version != metadata["Version"].replace("-", "_"):
                raise ValueError("Wheel filename differs from package metadata")
            if not all(re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*", tag)
                       for tag in (python_tag, abi_tag, platform_tag)):
                raise ValueError("Invalid wheel compatibility tags")
            wheel_name = metadata_name.removesuffix("METADATA") + "WHEEL"
            if [name for name in names if name.endswith(".dist-info/WHEEL")] != [wheel_name]:
                raise ValueError("Wheel must contain exactly one matching WHEEL metadata file")
            wheel_metadata = BytesParser().parsebytes(read(wheel_name))
            if wheel_metadata.get_all("Build") is not None:
                raise ValueError("Standard WHEEL metadata must not contain a Build tag")
            tags = {"-".join(items) for items in product(
                python_tag.split("."), abi_tag.split("."), platform_tag.split("."))}
            if set(wheel_metadata.get_all("Tag", [])) != tags:
                raise ValueError("WHEEL compatibility tags differ from filename")
        if source_manifest is not None:
            with open(source_manifest, "rb") as stream:
                expected_provenance = stream.read()
            embedded = read(f"{package}/BUILD_PROVENANCE.json")
            if embedded != expected_provenance:
                raise ValueError("Embedded source provenance differs from candidate manifest")
            provenance = json.loads(embedded)
            records = provenance["files"]
            if provenance.get("schema_version") != 1 or source_digest(records) != provenance["source_tree_sha256"]:
                raise ValueError("Source provenance digest mismatch")
            if package.startswith("python/"):
                with tarfile.open(path, "r:gz") as archive:
                    if source_files(archive) != records:
                        raise ValueError("Source archive differs from candidate source manifest")
            else:
                # Verify the wheel's directly copied Python, notices and data
                # against the same sources used for the native build.
                mapped = {}
                for record in records:
                    name = record["path"]
                    if name.startswith("python/gmatpy/"):
                        mapped[name[len("python/"):]] = record
                    elif name.startswith("application/data/") and (profile is None or
                            name[len("application/data/"):] in profile["data_files"]):
                        mapped["gmatpy/data/" + name[len("application/data/"):]] = record
                for name, record in mapped.items():
                    if hashlib.sha256(read(name)).hexdigest() != record["sha256"]:
                        raise ValueError(f"Wheel/source hash mismatch: {name}")
            print(f"SOURCE_IDENTITY_OK: {provenance['source_revision']} + "
                  f"{provenance['source_tree_sha256']}")
        for component in code["components"]:
            if component.get("license_file"):
                contents = read(f"{package}/licenses/{component['license_file']}")
                if hashlib.sha256(contents).hexdigest() != component["license_file_sha256"]:
                    raise ValueError(f"Code license hash mismatch: {component['id']}")
        data = json.loads(read(f"{package}/licenses/DATA_MANIFEST.json"))
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported data-manifest schema")
        records = data["files"]
        entries = {record["path"]: record for record in records}
        if len(entries) != len(records):
            raise ValueError("Duplicate data-manifest paths")
        actual = {name[len(data_prefix):] for name in names if name.startswith(data_prefix)}
        expected = {name for name, record in entries.items() if record["status"] != "excluded"}
        if profile is not None:
            selected = profile["data_files"]
            if len(selected) != len(set(selected)) or not set(selected) <= expected:
                raise ValueError("Invalid profile data inventory")
            if set(selected) != expected:
                raise ValueError("Build profile has an unexpected data selection")
        if is_wheel and len(expected) != 17:
            raise ValueError("Standard full headless wheel must include all 17 packaged data files")
        if actual != expected:
            raise ValueError(f"Data inventory mismatch: extra={sorted(actual-expected)}, "
                             f"missing={sorted(expected-actual)}")
        blockers = []
        verified = {"verified_unmodified_naif", "licensing_verified",
                    "documented_reuse_basis"}
        for relative in sorted(actual):
            parts = PurePosixPath(relative).parts
            if ".." in parts or relative.startswith("/"):
                raise ValueError(f"Unsafe inventory path: {relative}")
            record = entries[relative]
            digest = hashlib.sha256(read(data_prefix + relative)).hexdigest()
            if digest != record["sha256"]:
                raise ValueError(f"Data hash mismatch: {relative}")
            if record.get("license_file"):
                contents = read(f"{package}/licenses/{record['license_file']}")
                if hashlib.sha256(contents).hexdigest() != record["license_file_sha256"]:
                    raise ValueError(f"Data terms hash mismatch: {relative}")
            for notice, digest in record.get("additional_notice_sha256", {}).items():
                contents = read(f"{package}/licenses/{notice}")
                if hashlib.sha256(contents).hexdigest() != digest:
                    raise ValueError(f"Additional data notice hash mismatch: {notice}")
            if record["status"] not in verified:
                blockers.append(f"{relative}: {record['status']}")
        for name in names:
            basename = PurePosixPath(name).name
            if name.startswith(data_prefix) and (basename.startswith("SpaceWeather") or
                                                basename in {"SchattenPredict.txt", "marini.dat"}):
                raise ValueError(f"Excluded optional dataset shipped: {name}")
        if "src/base/solarsys/msise90_sub.for" in names:
            raise ValueError("Unreplaced upstream Fortran spline source shipped")
        if package.startswith("python/"):
            if read("application/License.txt") != apache:
                raise ValueError("Source-archive GMAT license copies differ")
            for record in code.get("numerical_remediation", {}).get("changed_files", []):
                if hashlib.sha256(read(record["path"])).hexdigest() != record["sha256"]:
                    raise ValueError(f"Remediated source hash mismatch: {record['path']}")
            for record in data.get("generators", []):
                if hashlib.sha256(read(record["path"])).hexdigest() != record["sha256"]:
                    raise ValueError(f"Data generator hash mismatch: {record['path']}")
        code_blockers = [f"{item['id']}: {item['notes']}"
                         for item in code.get("publication_review", [])
                         if item["status"] != "resolved"]
        print(f"DISTRIBUTION_CONTENTS_OK: {len(actual)} data files; licenses, notices, "
              f"hashes and exclusions checked; {len(blockers)} data and "
              f"{len(code_blockers)} code release-review items")
        blockers.extend(code_blockers)
        if release and blockers:
            raise ValueError("Release review unresolved:\n  " + "\n  ".join(blockers))
        return blockers


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact")
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--source-manifest", help="Require exact embedded candidate provenance and source hashes")
    args = parser.parse_args()
    try:
        check(args.artifact, release=args.release, source_manifest=args.source_manifest)
    except (ValueError, KeyError, json.JSONDecodeError) as error:
        parser.exit(1, f"{error}\n")
