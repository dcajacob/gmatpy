"""Verify an experimental Windows x64 wheel using an existing MSVC dumpbin.

Run from an x64 Developer Command Prompt; this installs nothing. The ordinary
source/data/notice checker runs first. This is artifact verification, not release
clearance or a replacement for installed numerical tests.
"""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

from check_distribution import check as check_distribution


def check(path, *, source_manifest=None):
    check_distribution(path, source_manifest=source_manifest)
    with zipfile.ZipFile(path) as wheel, tempfile.TemporaryDirectory() as tmp:
        assert wheel.filename.endswith('-win_amd64.whl'), 'Expected a Windows x64 wheel'
        names = wheel.namelist()
        metadata = [n for n in names if n.endswith('.dist-info/WHEEL')]
        assert len(metadata) == 1
        assert any(line.startswith('Tag: ') and line.endswith('-win_amd64')
                   for line in wheel.read(metadata[0]).decode().splitlines())
        binaries = [n for n in names if n.lower().endswith(('.dll', '.pyd'))]
        expected = {'gmatpy/_native/libGmatBase.dll', 'gmatpy/_native/libGmatUtil.dll',
                    'gmatpy/_native/_gmat_py.pyd'}
        assert set(binaries) == expected, binaries
        assert not any(n.lower().endswith(('.lib', '.exp', '.pdb', '.exe')) for n in names)
        wheel.extractall(tmp)  # Distribution checker already validates archive paths.
        bundled = {Path(n).name.lower() for n in binaries}
        for name in binaries:
            binary = Path(tmp) / name
            headers = subprocess.check_output(['dumpbin', '/headers', str(binary)], text=True)
            assert re.search(r'8664 machine \(x64\)', headers), name
            exports = subprocess.check_output(['dumpbin', '/exports', str(binary)], text=True)
            assert 'FileUpdaterSVN' not in exports, name
            output = subprocess.check_output(['dumpbin', '/dependents', str(binary)], text=True)
            dependencies = re.findall(r'^\s+([^\s]+\.dll)\s*$', output, re.I | re.M)
            assert dependencies, output
            for dependency in dependencies:
                lower = dependency.lower()
                assert not any(s in lower for s in ('xerces', 'wxbase', 'wxmsw', 'qt5', 'qt6')), dependency
                assert lower in bundled or lower.startswith(('api-ms-', 'ext-ms-', 'python3')) or (Path('C:/Windows/System32') / dependency).is_file(), dependency
            print(name, 'depends on', ', '.join(dependencies))
        print('WINDOWS_WHEEL_OK: x64 PE binaries, required engine DLLs, no GUI/Xerces imports')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifact')
    parser.add_argument('--source-manifest')
    args = parser.parse_args()
    check(args.artifact, source_manifest=args.source_manifest)
