"""Check a single-architecture Mach-O wheel with Apple's lipo/otool/nm.

This verifies declared minimum OS and relocation; it cannot prove execution on
older macOS releases. Installed tests must run separately on the native runner.
"""
import argparse,re,subprocess,tempfile,zipfile
from pathlib import Path
from check_distribution import check as check_distribution


def check(path, *, arch, source_manifest=None, deployment_target='11.0'):
    check_distribution(path,source_manifest=source_manifest)
    def run(*args):return subprocess.check_output(list(map(str,args)),text=True)
    with zipfile.ZipFile(path) as wheel,tempfile.TemporaryDirectory() as directory:
        names=wheel.namelist()
        assert Path(path).name.endswith(f'-macosx_11_0_{arch}.whl'),Path(path).name
        binaries=[n for n in names if n.endswith(('.so','.dylib'))]
        assert set(binaries)=={'gmatpy/_native/_gmat_py.so','gmatpy/_native/libGmatBase.dylib','gmatpy/_native/libGmatUtil.dylib'},binaries
        wheel.extractall(directory)
        for name in binaries:
            binary=Path(directory)/name
            assert run('lipo','-archs',binary).strip()==arch,name
            loads=run('otool','-l',binary)
            minimums=re.findall(r'\b(?:minos|version) (\d+\.\d+(?:\.\d+)?)',loads)
            assert minimums,(name,loads)
            # Restrict specifically the OS load command, not dylib version fields.
            os_min=re.findall(r'cmd LC_(?:BUILD_VERSION|VERSION_MIN_MACOSX)\b(?:(?!\nLoad command).)*?\b(?:minos|version) (\d+\.\d+(?:\.\d+)?)',loads,re.S)
            assert os_min and all(tuple(map(int,v.split('.'))) <= tuple(map(int,deployment_target.split('.')))+(0,) for v in os_min),(name,os_min)
            rpaths=re.findall(r'cmd LC_RPATH\b(?:(?!\nLoad command).)*?\bpath ([^\n]+?) \(offset',loads,re.S)
            assert all(r.startswith(('@loader_path','@rpath')) for r in rpaths),(name,rpaths)
            deps=[]
            for line in run('otool','-L',binary).splitlines()[1:]:
                dependency=line.strip().split(' (',1)[0];deps.append(dependency)
                assert not re.search('xerces|libQt|libwx|libgtk',dependency,re.I),dependency
                assert dependency.startswith(('/usr/lib/','/System/Library/','@loader_path/','@rpath/')),dependency
                if dependency.startswith(('@loader_path/','@rpath/')):
                    assert Path(dependency).name in {Path(n).name for n in binaries},dependency
            if name.endswith('.dylib'):
                ids=run('otool','-D',binary).splitlines()[1:]
                assert ids==['@rpath/'+Path(name).name] or ids==['@loader_path/'+Path(name).name],ids
            symbols=run('nm','-g',binary)
            assert 'FileUpdaterSVN' not in symbols
            if name=='gmatpy/_native/libGmatBase.dylib':
                assert '_spkezr_c' in symbols and '_furnsh_c' in symbols,'Full SPICE implementation missing'
            print(name,'architecture',arch,'minimum OS',os_min,'rpaths',rpaths,'dependencies',deps)
        print('MACOS_WHEEL_OK: native single architecture, relative load paths, system-only external dependencies')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('artifact');p.add_argument('--arch',required=True,choices=['arm64','x86_64']);p.add_argument('--source-manifest');a=p.parse_args();check(a.artifact,arch=a.arch,source_manifest=a.source_manifest)
