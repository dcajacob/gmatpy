"""Rebuild all official Windows CSPICE N0067 sources using existing MSVC x64.

No prebuilt NAIF object/library is extracted. Run inside an x64 Developer shell.
The archive, every input, ABI probe and final native library are receipt-bound.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import urllib.request
import zipfile

ARCHIVE = {
    "url": "https://naif.jpl.nasa.gov/pub/naif/toolkit/C/PC_Windows_VisualC_64bit/packages/cspice.zip",
    "sha256": "98d60b814b412fa55294aeaaeb7dab46d849cc87a8b709ffe835d08de17625dc",
    "bytes": 36519028,
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root, archive=None, jobs=2):
    assert os.name == "nt" and platform.machine().upper() == "AMD64"
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    if archive is None:
        archive = root / "official.zip"
        with urllib.request.urlopen(ARCHIVE["url"], timeout=90) as response, archive.open("wb") as out:
            shutil.copyfileobj(response, out)
    assert archive.stat().st_size == ARCHIVE["bytes"] and sha(archive) == ARCHIVE["sha256"]
    include, source, objects, lib = [root / name for name in ("include", "native-source", "objects", "lib")]
    for directory in (include, source, objects, lib):
        directory.mkdir()
    records = []
    with zipfile.ZipFile(archive) as package:
        for name in package.namelist():
            path = PurePosixPath(name)
            assert not path.is_absolute() and ".." not in path.parts
            public = name.startswith("cspice/include/") and path.suffix == ".h"
            native = name.startswith("cspice/src/cspice/") and path.suffix in (".c", ".h")
            if not (public or native):
                continue
            dest = (include if public else source) / path.name
            assert not dest.exists()
            dest.write_bytes(package.read(name))
            records.append({"path": name, "sha256": sha(dest)})
    assert "#define   CSPICE_PC_64BIT_MS" in (include / "SpiceZpl.h").read_text()
    compiler = shutil.which("cl")
    librarian = shutil.which("lib")
    assert compiler and librarian
    # NAIF's Windows recipe uses these defines and disables zzsecprt optimization.
    # /MD matches GMAT/Python's shared CRT; no compile-time floating-point relaxation.
    flags = ["/nologo", "/c", "/MD", "/D_COMPLEX_DEFINED", "/DMSDOS", "/DOMIT_BLANK_CC", "/DNON_ANSI_STDIO"]
    files = sorted(source.glob("*.c"))
    assert len(files) == 2229, len(files)
    def compile_one(path):
        obj = objects / (path.stem + ".obj")
        command = [compiler, *flags, "/Od" if path.name == "zzsecprt.c" else "/O2", "/I" + str(include), str(path), "/Fo" + str(obj)]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(str(path) + "\n" + result.stdout + result.stderr)
        return obj
    compiled = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        for number, obj in enumerate(pool.map(compile_one, files), 1):
            compiled.append(obj)
            if number % 200 == 0:
                print("CSPICE native compile", number, "/", len(files), flush=True)
    library = lib / "cspice.lib"
    response_file = root / "objects.rsp"
    response_file.write_text("\n".join('"' + str(obj) + '"' for obj in compiled))
    subprocess.run([librarian, "/nologo", "/MACHINE:X64", "/OUT:" + str(library), "@" + str(response_file)], check=True)
    members = subprocess.check_output([librarian, "/nologo", "/list", str(library)], text=True).splitlines()
    assert len(members) == len(compiled), len(members)
    headers = subprocess.check_output(["dumpbin", "/headers", str(compiled[0])], text=True)
    assert "8664 machine (x64)" in headers
    probe = root / "abi-probe.c"
    probe.write_text(r'''#include "SpiceUsr.h"
#include "f2c.h"
#include <stdio.h>
#include <float.h>
int main(void) {
 unsigned int one=1;
 if(sizeof(void*)!=8 || sizeof(SpiceInt)!=4 || sizeof(integer)!=4 || sizeof(long)!=4 || sizeof(double)!=8 || DBL_MANT_DIG!=53 || DBL_MAX_EXP!=1024 || *(unsigned char*)&one!=1) return 2;
 printf("{\"SpiceInt\":4,\"f2c_integer\":4,\"long\":4,\"pointer\":8,\"double\":8,\"little_endian\":true,\"toolkit\":\"%s\"}\n",tkvrsn_c("TOOLKIT"));
 return 0;
}
''')
    exe = root / "abi-probe.exe"
    subprocess.run([compiler, "/nologo", "/MD", "/I" + str(include), str(probe), str(library), "/Fe" + str(exe)], cwd=root, check=True)
    abi = json.loads(subprocess.check_output([str(exe)], text=True))
    assert abi["toolkit"] == "CSPICE_N0067", abi
    version = subprocess.run([compiler], capture_output=True, text=True)
    record = {"target": "windows-x86_64", "archive": ARCHIVE, "native_sources": records,
              "native_machine": platform.machine(), "compiler": version.stderr.strip(), "compile_flags": flags,
              "zzsecprt_optimization": "/Od", "other_optimization": "/O2", "object_count": len(compiled),
              "library_sha256": sha(library), "header_sha256": {p.name: sha(p) for p in sorted(include.glob("*.h"))},
              "abi": abi, "object_architecture": headers,
              "note": "All 2229 official Windows N0067 C files rebuilt natively; precompiled archive members are not used."}
    (root / "BUILD_DEPENDENCY.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print("CSPICE_NATIVE_OK", record["target"], record["library_sha256"], abi, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--jobs", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    build(args.output, args.archive, args.jobs)
