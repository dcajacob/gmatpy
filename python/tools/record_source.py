"""Bind a local candidate to the exact source archive inputs (standard library).

Build an sdist, then run this tool with its Git revision and the SHA-256 of the
full working-tree manifest. Write the result to python/gmatpy/BUILD_PROVENANCE.json
in an isolated source snapshot, rebuild the sdist, and build the wheel from that
sdist. PKG-INFO and this provenance file are excluded from the source digest to
avoid self-reference. This records identity, not a source-to-binary proof.
"""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile


PROVENANCE = "python/gmatpy/BUILD_PROVENANCE.json"


def source_files(archive):
    records = []
    seen = set()
    roots = set()
    for member in archive.getmembers():
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or str(path) != member.name.rstrip("/"):
            raise ValueError(f"Unsafe source path: {member.name}")
        roots.add(path.parts[0])
        if member.isdir():
            continue
        if not member.isfile():
            raise ValueError(f"Unsupported source member: {member.name}")
        if len(path.parts) < 2:
            raise ValueError("Source files must have a top-level directory")
        name = "/".join(path.parts[1:])
        if name in seen:
            raise ValueError(f"Duplicate source member: {name}")
        seen.add(name)
        if name in {"PKG-INFO", PROVENANCE}:
            continue
        with archive.extractfile(member) as stream:
            digest = hashlib.sha256(stream.read()).hexdigest()
        records.append({"path": name, "sha256": digest, "size": member.size,
                        "mode": member.mode & 0o777})
    if len(roots) != 1:
        raise ValueError("Source archive must have a single top-level directory")
    return sorted(records, key=lambda record: record["path"])


def source_digest(records):
    return hashlib.sha256(json.dumps(records, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def record(path, revision, working_tree_sha256):
    for name, value in (("revision", revision), ("working-tree SHA-256", working_tree_sha256)):
        length = 40 if name == "revision" else 64
        if len(value) != length or any(c not in "0123456789abcdef" for c in value):
            raise ValueError(f"Invalid {name}")
    with tarfile.open(path, "r:gz") as archive:
        records = source_files(archive)
    return {"schema_version": 1, "source_revision": revision,
            "working_tree_manifest_sha256": working_tree_sha256,
            "source_tree_sha256": source_digest(records), "files": records}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sdist")
    parser.add_argument("--revision", required=True)
    parser.add_argument("--working-tree-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest = record(args.sdist, args.revision, args.working_tree_sha256)
    Path(args.output).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"SOURCE_TREE_SHA256: {manifest['source_tree_sha256']}")
