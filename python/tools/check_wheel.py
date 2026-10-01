"""Check a repaired Linux wheel: python python/tools/check_wheel.py path.whl."""

from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile


def check(path):
    with zipfile.ZipFile(path) as wheel, tempfile.TemporaryDirectory() as directory:
        names = wheel.namelist()
        assert "gmat_hpop/_native/gmat_py.py" in names
        assert any(name.startswith("gmat_hpop/_native/_gmat_py") for name in names)
        for library in ("GmatBase", "GmatUtil"):
            prefix = f"gmat_hpop/_native/lib{library}.so"
            assert prefix not in names, "Unversioned linker alias duplicates the runtime library"
            assert any(name.startswith(prefix + ".") for name in names), "Runtime library missing"
        assert "gmat_hpop/data/gravity/earth/EGM96.cof" in names
        assert "gmat_hpop/data/planetary_ephem/de/leDE1941.405" in names
        assert not any("graphics/" in name or "GmatConsole" in name or "GmatQt" in name for name in names)
        assert not any("xerces" in name.lower() for name in names), "Xerces is excluded"
        wheel.extractall(directory)
        libraries = []
        for name in names:
            file = Path(directory) / name
            if file.is_file() and file.read_bytes()[:4] == b"\x7fELF":
                libraries.append(file)
                dynamic = subprocess.check_output(["readelf", "-d", file], text=True)
                assert not re.search(r"lib(?:Qt|wx|gtk|X11|GL\.so|xerces)", dynamic), name
                symbols = subprocess.check_output(["nm", "-D", file], text=True)
                assert "FileUpdaterSVN" not in symbols, name
                for line in dynamic.splitlines():
                    if "RPATH" in line or "RUNPATH" in line:
                        entries = line.split("[", 1)[1].split("]", 1)[0].split(":")
                        assert all(entry.startswith("$ORIGIN") for entry in entries), line
                loaded = subprocess.check_output(["ldd", file], text=True)
                assert "not found" not in loaded, loaded
                assert "/home/" not in loaded and "/tmp/gmat-python-hpop/" not in loaded, loaded
        assert len(libraries) >= 3
        print(f"WHEEL_OK: {len(libraries)} native libraries, no GUI/Xerces/updater dependencies, relocatable paths")


if __name__ == "__main__":
    check(sys.argv[1])
