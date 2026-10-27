"""Build the full Windows x64 wheel from a frozen source and test installed bytes.

Uses the existing MSVC x64 environment; all outputs stay outside the checkout.
Python/GMAT/compiler directories are removed from runtime PATH during installed
checks. Compiler access is restored only for the installed DLL spline harness.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import sysconfig
import tarfile

from qualify import digest, run


def qualify(args):
    assert os.name == 'nt' and platform.machine().upper() == 'AMD64'
    assert platform.python_implementation() == 'CPython' and not sysconfig.get_config_var('Py_GIL_DISABLED')
    assert platform.python_version() == args.python_version
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', SOURCE_DATE_EPOCH='1790812800',
               CMAKE_BUILD_PARALLEL_LEVEL='2', CMAKE_GENERATOR='Ninja', PYTHONUTF8='1')
    env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env['PATH']
    for name in ('PYTHONPATH', 'GMAT_PY_PROFILE'):
        env.pop(name, None)
    source_archive = args.sdist.resolve()
    source_root = output / 'source'
    source_root.mkdir()
    with tarfile.open(source_archive) as archive:
        archive.extractall(source_root, filter='data')
    sources = list(source_root.iterdir())
    assert len(sources) == 1
    source = sources[0]
    ci, tools = source / 'python/ci', source / 'python/tools'
    manifest = source / 'python/gmatpy/BUILD_PROVENANCE.json'
    run([sys.executable, tools / 'check_distribution.py', source_archive, '--source-manifest', manifest],
        cwd=output, env=env, log=output / 'sdist-check.log')
    spice = output / 'cspice'
    run([sys.executable, ci / 'build_windows_cspice.py', '--output', spice],
        cwd=output, env=env, log=output / 'cspice-build.log')
    dependency = json.loads((spice / 'BUILD_DEPENDENCY.json').read_text())
    assert dependency['target'] == 'windows-x86_64'
    assert digest(spice / 'lib/cspice.lib') == dependency['library_sha256']
    shutil.copy2(spice / 'BUILD_DEPENDENCY.json', output / 'CSPICE_BUILD_DEPENDENCY.json')
    interpreter = {'version': platform.python_version(), 'implementation': platform.python_implementation(),
                   'executable': sys.executable, 'pointer_bits': 64, 'gil_disabled': False,
                   'sys_version': sys.version, 'source': 'actions/setup-python standard x64 distribution'}
    (output / 'INTERPRETER.json').write_text(json.dumps(interpreter, indent=2) + '\n')
    run([sys.executable, '-m', 'pip', 'freeze'], cwd=output, env=env, log=output / 'python-tools.txt')
    dest = output / 'extended'
    dest.mkdir()
    wheels_dir = dest / 'wheelhouse'
    native = dest / 'native'
    run([sys.executable, '-m', 'build', '--wheel', '--no-isolation', '--outdir', wheels_dir, source,
         '-Cbuild-dir=' + str(native), '-Ccmake.define.CSPICE_DIR=' + str(spice),
         '-Ccmake.define.GMAT_PY_EXPERIMENTAL_WINDOWS=ON'], cwd=output, env=env, log=dest / 'build.log')
    wheels = list(wheels_dir.glob('*.whl'))
    assert len(wheels) == 1
    wheel = wheels[0]
    run([sys.executable, tools / 'check_windows_wheel.py', wheel, '--source-manifest', manifest],
        cwd=output, env=env, log=dest / 'binary-contents-check.log')
    run([sys.executable, tools / 'check_distribution.py', wheel, '--release', '--source-manifest', manifest],
        cwd=output, env=env, log=dest / 'release-preflight.log')
    test_env = dest / 'test-env'
    run([sys.executable, '-m', 'venv', '--without-pip', test_env], cwd=output, env=env, log=dest / 'venv.log')
    test_python = test_env / 'Scripts/python.exe'
    run([sys.executable, '-m', 'pip', '--python', test_python, 'install', wheel, 'pytest==9.1.1',
         'iniconfig==2.3.1', 'packaging==26.0', 'pluggy==1.6.0', 'pygments==2.19.2', 'colorama==0.4.6'],
        cwd=output, env=env, log=dest / 'install.log')
    outside = dest / 'outside-source'
    outside.mkdir()
    clean_env = dict(env)
    winroot = Path(os.environ['SystemRoot'])
    clean_env['PATH'] = os.pathsep.join(map(str, [test_python.parent, winroot / 'System32', winroot]))
    code = '''import hashlib,importlib.util,pathlib,zipfile,sys
root=pathlib.Path(importlib.util.find_spec('gmatpy').origin).parent.parent
assert not root.is_relative_to(pathlib.Path(sys.argv[2]))
with zipfile.ZipFile(sys.argv[1]) as z:
 for n in z.namelist():
  if n.startswith('gmatpy/') and not n.endswith('/'):
   assert hashlib.sha256((root/n).read_bytes()).digest()==hashlib.sha256(z.read(n)).digest(),n
import gmatpy
print('INSTALLED_BYTES_AND_IMPORT_OK',root,gmatpy.__version__)
'''
    run([test_python, '-I', '-c', code, wheel, source], cwd=outside, env=clean_env, log=dest / 'installed-bytes.log')
    run([test_python, '-m', 'pytest', '-q', '-ra', '--import-mode=prepend', source / 'python/tests'],
        cwd=outside, env=env, log=dest / 'pytest.log', timeout=600)
    run([test_python, ci / 'sample_states.py', dest / 'states.json'], cwd=outside, env=clean_env,
        log=dest / 'sample.log', timeout=180)
    run([test_python, ci / 'check_states.py', dest / 'states.json'], cwd=outside, env=clean_env,
        log=dest / 'state-comparison.json')
    import_libraries = list(native.glob('engine/src/gmatutil/GmatUtil.lib'))
    assert len(import_libraries) == 1, import_libraries
    run([test_python, ci / 'verify_splines.py', source, dest / 'spline', import_libraries[0]],
        cwd=outside, env=env, log=dest / 'spline.log', timeout=180)
    profile = {'wheel': wheel.name, 'sha256': digest(wheel), 'bytes': wheel.stat().st_size,
               'tests': (dest / 'pytest.log').read_text().splitlines()[-1],
               'state_comparison': json.loads((dest / 'state-comparison.json').read_text()),
               'spline_comparison': json.loads((dest / 'spline/RESULTS.json').read_text()),
               'msise_comparison': {'status': 'not_run', 'reason': 'MSISE C helper symbols are not exported by the installed Windows DLL; atmospheric propagation is covered by installed tests and state comparison.'}}
    result = {'target': 'windows-x86_64', 'python_minor': '.'.join(map(str, sys.version_info[:2])),
              'interpreter': interpreter, 'platform': platform.platform(), 'release_preflight': 'passed',
              'sdist_sha256': digest(source_archive),
              'source_tree_sha256': json.loads(manifest.read_text())['source_tree_sha256'],
              'cspice_library_sha256': dependency['library_sha256'], 'profiles': {'extended': profile},
              'runtime_path': clean_env['PATH'], 'runner_image': os.environ.get('ImageVersion')}
    (output / 'RESULTS.json').write_text(json.dumps(result, indent=2) + '\n')
    files = [*dest.glob('*.log'), dest / 'state-comparison.json', dest / 'states.json',
             dest / 'spline/RESULTS.json', output / 'CSPICE_BUILD_DEPENDENCY.json',
             output / 'INTERPRETER.json', output / 'python-tools.txt', output / 'RESULTS.json']
    evidence = {str(p.relative_to(output)): digest(p) for p in files}
    (output / 'EVIDENCE_SHA256.json').write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n')
    payload = output / 'payload'
    payload.mkdir()
    for p in [wheel, *files, output / 'EVIDENCE_SHA256.json']:
        name = 'spline-RESULTS.json' if p == dest / 'spline/RESULTS.json' else p.name
        assert not (payload / name).exists()
        shutil.copy2(p, payload / name)
    assert sum(p.stat().st_size for p in payload.iterdir()) <= 90000000
    print('WINDOWS_QUALIFIED', json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdist', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--python-version', required=True)
    qualify(parser.parse_args())
