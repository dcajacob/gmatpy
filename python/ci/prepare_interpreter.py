"""Retrieve an exact standard-ABI CPython build into a fresh isolated directory."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import urllib.parse
import urllib.request


def prepare(manifest, minor, target, output, archive=None):
    record = json.loads(manifest.read_text())["interpreters"][minor + "/" + target]
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = archive.resolve() if archive else output / record["filename"]
    if archive is None:
        url = urllib.parse.urlsplit(record["url"])
        if url.scheme != "https" or url.hostname != "github.com" or not url.path.startswith("/astral-sh/python-build-standalone/releases/download/"):
            raise ValueError("Unexpected interpreter origin")
        with urllib.request.urlopen(record["url"], timeout=120) as response, source.open("xb") as stream:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > record["bytes"]:
                    raise ValueError("Interpreter download exceeded expected size")
                stream.write(chunk)
    with source.open("rb") as stream:
        if source.stat().st_size != record["bytes"] or hashlib.file_digest(stream, "sha256").hexdigest() != record["sha256"]:
            raise ValueError("Interpreter archive differs from pinned receipt")
    with tarfile.open(source) as bundle:
        bundle.extractall(output, filter="data")
    python = output / "python/bin/python3"
    code = "import json,sys,sysconfig; print(json.dumps({'version':'.'.join(map(str,sys.version_info[:3])),'implementation':sys.implementation.name,'gil_disabled':bool(sysconfig.get_config_var('Py_GIL_DISABLED')),'soabi':sysconfig.get_config_var('SOABI')}))"
    identity = json.loads(subprocess.check_output([str(python), "-I", "-c", code], text=True))
    if identity["version"] != record["version"] or identity["implementation"] != "cpython" or identity["gil_disabled"]:
        raise ValueError("Interpreter is not the requested standard CPython build")
    (output / "INTERPRETER.json").write_text(json.dumps({**record, "runtime": identity}, indent=2) + "\n")
    print(python, flush=True)
    return python


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("interpreters.json"))
    parser.add_argument("--minor", required=True, choices=("3.12", "3.13", "3.14", "3.15"))
    parser.add_argument("--target", required=True, choices=("linux-x86_64", "linux-arm64", "macos-x86_64", "macos-arm64"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    prepare(args.manifest, args.minor, args.target, args.output, args.archive)
