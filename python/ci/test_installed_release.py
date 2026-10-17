"""Test one final release wheel in an empty venv without native compilation."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import sysconfig
import tarfile

from reuse_wheels import VERSION, encoded, require, sha
from release_bundle import check_manifest


def run(args, cwd, env, output, timeout=600):
    with output.open('w') as stream:
        subprocess.run(list(map(str, args)), cwd=cwd, env=env, stdout=stream,
                       stderr=subprocess.STDOUT, timeout=timeout, check=True)


def test_installed(bundle, manifest_path, target, minor, output, wheelhouse=None):
    manifest = json.loads(manifest_path.read_text())
    check_manifest(manifest)
    require(platform.python_implementation() == 'CPython' and not sysconfig.get_config_var('Py_GIL_DISABLED'),
            'Requires standard CPython')
    expected = json.loads(Path(__file__).with_name('interpreters.json').read_text())['interpreters'][minor + '/' + target]
    require(platform.python_version() == expected['version'], 'Unqualified interpreter patch')
    system, arch = target.split('-')
    require(platform.system() == ('Linux' if system == 'linux' else 'Darwin'), 'Wrong native OS')
    require(platform.machine().lower() == ('aarch64' if arch == 'arm64' and system == 'linux' else arch),
            'Wrong native architecture')
    record = next(r for r in manifest['files'] if r.get('target') == target and r.get('minor') == minor)
    wheel = (bundle / record['file']).resolve()
    require(sha(wheel) == record['sha256'], 'Final wheel hash differs')
    source_archive = (bundle / f'gmatpy-{VERSION}.tar.gz').resolve()
    require(sha(source_archive) == manifest['packaging_source']['source_archive_sha256'], 'Final sdist differs')
    output = output.resolve()
    output.mkdir(exist_ok=False)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    for name in ('PYTHONPATH', 'LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH'):
        env.pop(name, None)
    with tarfile.open(source_archive) as archive:
        archive.extractall(output / 'source', filter='data')
    source = output / 'source' / f'gmatpy-{VERSION}'
    run([sys.executable, '-m', 'venv', '--without-pip', output / 'venv'], output, env, output / 'venv.log')
    python = output / 'venv/bin/python'
    install = [sys.executable, '-m', 'pip', '--python', python, 'install', '--only-binary=:all:',
               wheel, 'pytest==9.1.1', 'iniconfig==2.3.1', 'packaging==26.0', 'pluggy==1.6.0', 'pygments==2.19.2']
    if wheelhouse:
        install.extend(['--no-index', '--find-links', wheelhouse.resolve()])
    run(install, output, env, output / 'install.log')
    outside = output / 'outside-source'
    outside.mkdir()
    code = '''import gmatpy,importlib.metadata,pathlib,hashlib,zipfile,sys
assert gmatpy.__version__ == importlib.metadata.version('gmatpy') == '0.2.1'
root=pathlib.Path(gmatpy.__file__).parent.parent
assert not str(root).startswith(sys.argv[2])
with zipfile.ZipFile(sys.argv[1]) as z:
 for n in z.namelist():
  if n.startswith('gmatpy/') and not n.endswith('/'):
   assert hashlib.sha256((root/n).read_bytes()).digest()==hashlib.sha256(z.read(n)).digest(),n
print('INSTALLED_BYTES_AND_VERSIONS_OK',root)
'''
    run([python, '-c', code, wheel, source], outside, env, output / 'installed-bytes.log')
    run([python, '-m', 'pytest', '-q', '-ra', '--import-mode=prepend', source / 'python/tests'],
        outside, env, output / 'pytest.log')
    tests = (output / 'pytest.log').read_text()
    require('209 passed' in tests and 'failed' not in tests and 'skipped' not in tests,
            'Incomplete final installed-wheel test outcome')
    run([python, source / 'python/ci/sample_states.py', output / 'states.json'], outside, env, output / 'sample.log', 180)
    run([python, source / 'python/ci/check_states.py', output / 'states.json'], outside, env, output / 'state-comparison.json', 180)
    checker = source / 'python/tools' / ('check_wheel.py' if system == 'linux' else 'check_macos_wheel.py')
    command = [sys.executable, checker, wheel, '--source-manifest', source / 'python/gmatpy/BUILD_PROVENANCE.json']
    if system == 'macos':
        command.extend(['--arch', arch])
    run(command, outside, env, output / 'binary-check.log')
    result = {'schema_version': 1, 'version': VERSION, 'target': target, 'minor': minor,
              'interpreter_version': platform.python_version(), 'wheel': record,
              'packaging_source_revision': manifest['packaging_source']['source_revision'],
              'native_build_source_revision': manifest['native_build_source_revision'], 'native_recompiled': False,
              'installed_bytes_and_versions': 'passed', 'tests': tests.splitlines()[-1],
              'state_comparison': json.loads((output / 'state-comparison.json').read_text()),
              'binary_check': 'passed', 'result': 'passed'}
    (output / 'RESULTS.json').write_bytes(encoded(result))
    print('FINAL_RELEASE_CELL_OK', json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'manifest', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--minor', required=True)
    parser.add_argument('--wheelhouse', type=Path)
    args = parser.parse_args()
    test_installed(args.bundle.resolve(), args.manifest.resolve(), args.target, args.minor, args.output, args.wheelhouse)
