"""Negative tests for publication authorization boundaries; no network calls."""
import copy
import importlib.util
import itertools
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'python/ci'))
spec = importlib.util.spec_from_file_location('release_guard_021', Path(__file__).with_name('release_021.py'))
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def manifest():
    return json.loads((ROOT / '.github/release/pypi-0.2.1.json').read_text())


def run_and_jobs():
    run = {'repository': {'full_name': guard.REPOSITORY}, 'event': 'workflow_dispatch',
           'head_sha': 'a' * 40, 'head_branch': 'main', 'path': guard.QUALIFICATION_WORKFLOW,
           'run_attempt': 1, 'status': 'completed', 'conclusion': 'success'}
    jobs = [{'name': n, 'status': 'completed', 'conclusion': 'success'} for n in
            ['stage', *[f'installed ({t})' for t in guard.TARGETS]]]
    return run, jobs


def test_accept_exact_completed_native_jobs():
    run, jobs = run_and_jobs()
    guard.verify_qualification(run, jobs, 'a' * 40)


@pytest.mark.parametrize('field,value', [('event', 'push'), ('head_sha', 'b' * 40),
                                        ('head_branch', 'other'), ('path', 'other.yml'),
                                        ('run_attempt', 2), ('status', 'in_progress'),
                                        ('conclusion', 'failure')])
def test_reject_wrong_qualification_run(field, value):
    run, jobs = run_and_jobs()
    run[field] = value
    with pytest.raises(ValueError): guard.verify_qualification(run, jobs, 'a' * 40)


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'failed', 'skipped', 'extra', 'repository'])
def test_reject_incomplete_jobs(change):
    run, jobs = run_and_jobs()
    if change == 'missing': jobs.pop()
    if change == 'duplicate': jobs[1] = copy.deepcopy(jobs[2])
    if change == 'failed': jobs[1]['conclusion'] = 'failure'
    if change == 'skipped': jobs[1]['conclusion'] = 'skipped'
    if change == 'extra': jobs.append(copy.deepcopy(jobs[1]))
    if change == 'repository': run['repository']['full_name'] = 'other/repository'
    with pytest.raises(ValueError): guard.verify_qualification(run, jobs, 'a' * 40)


def cell_results():
    value = manifest()
    interpreters = json.loads((ROOT / 'python/ci/interpreters.json').read_text())['interpreters']
    records = []
    for f in value['files']:
        if not f['file'].endswith('.whl'): continue
        records.append({'result': 'passed', 'installed_bytes_and_versions': 'passed', 'binary_check': 'passed',
                        'version': '0.2.1', 'minor': f['minor'], 'target': f['target'],
                        'packaging_source_revision': value['packaging_source']['source_revision'],
                        'native_build_source_revision': value['native_build_source_revision'],
                        'native_recompiled': False, 'wheel': f,
                        'interpreter_version': interpreters[f['minor'] + '/' + f['target']]['version'],
                        'tests': '209 passed, 3 subtests passed in 1.0s'})
    return records


def test_accept_sixteen_exact_installed_cells():
    guard.verify_cell_records(cell_results(), manifest())


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'hash', 'version', 'packaging', 'native',
                                   'recompiled', 'skip', 'fail', 'count', 'count_prefix', 'subtests', 'patch', 'binary'])
def test_reject_unqualified_final_wheel_result(change):
    records = cell_results()
    if change == 'missing': records.pop()
    if change == 'duplicate': records[0] = copy.deepcopy(records[1])
    if change == 'hash': records[0]['wheel'] = dict(records[0]['wheel'], sha256='b' * 64)
    if change == 'version': records[0]['version'] = '0.2.1.dev0'
    if change == 'packaging': records[0]['packaging_source_revision'] = 'b' * 40
    if change == 'native': records[0]['native_build_source_revision'] = 'b' * 40
    if change == 'recompiled': records[0]['native_recompiled'] = True
    if change == 'skip': records[0]['tests'] += ', 1 skipped'
    if change == 'fail': records[0]['tests'] += ', 1 failed'
    if change == 'count': records[0]['tests'] = '208 passed, 3 subtests passed'
    if change == 'count_prefix': records[0]['tests'] = '1209 passed, 3 subtests passed'
    if change == 'subtests': records[0]['tests'] = '209 passed'
    if change == 'patch': records[0]['interpreter_version'] = '3.13.0'
    if change == 'binary': records[0]['binary_check'] = 'failed'
    with pytest.raises(ValueError): guard.verify_cell_records(records, manifest())


def public_state():
    value = manifest()
    return {'releases': {'0.2.0': [{'filename': n, 'digests': {'sha256': h}}
                                  for n, h in value['preserve_production_020'].items()]}}


def test_accept_unchanged_production_and_missing_new_release():
    assert guard.check_public_state(manifest(), public_state()) == set()


def test_allow_only_identical_partial_upload_resume():
    value, public = manifest(), public_state()
    f = value['files'][0]
    public['releases']['0.2.1'] = [{'filename': f['file'], 'size': f['bytes'], 'digests': {'sha256': f['sha256']}}]
    assert guard.check_public_state(value, public) == {f['file']}


@pytest.mark.parametrize('change', ['old_hash', 'old_missing', 'new_hash', 'new_size', 'new_name', 'yanked', 'duplicate'])
def test_reject_conflicting_production_state(change):
    value, public = manifest(), public_state()
    f = value['files'][0]
    existing = {'filename': f['file'], 'size': f['bytes'], 'digests': {'sha256': f['sha256']}}
    public['releases']['0.2.1'] = [existing]
    if change == 'old_hash': public['releases']['0.2.0'][0]['digests']['sha256'] = 'b' * 64
    if change == 'old_missing': public['releases']['0.2.0'].pop()
    if change == 'new_hash': existing['digests']['sha256'] = 'b' * 64
    if change == 'new_size': existing['size'] += 1
    if change == 'new_name': existing['filename'] = 'unexpected.whl'
    if change == 'yanked': existing['yanked'] = True
    if change == 'duplicate': public['releases']['0.2.1'].append(copy.deepcopy(existing))
    with pytest.raises(ValueError): guard.check_public_state(value, public)


@pytest.mark.parametrize('field', ['GITHUB_REPOSITORY', 'GITHUB_REF', 'GITHUB_EVENT_NAME', 'GITHUB_RUN_ATTEMPT',
                                  'GITHUB_WORKFLOW_REF', 'GITHUB_SHA'])
def test_reject_wrong_dispatch_context(field):
    env = {'GITHUB_REPOSITORY': guard.REPOSITORY, 'GITHUB_REF': 'refs/heads/main',
           'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_RUN_ATTEMPT': '1',
           'GITHUB_WORKFLOW_REF': guard.REPOSITORY + '/.github/workflows/publish-pypi.yml@refs/heads/main',
           'GITHUB_SHA': 'a' * 40}
    guard.context(env, 'publish-pypi.yml')
    env[field] = 'wrong'
    with pytest.raises(ValueError): guard.context(env, 'publish-pypi.yml')


def test_publisher_output_is_visible_inside_docker_action():
    workflow = (ROOT / '.github/workflows/publish-pypi.yml').read_text()
    assert '--output publish-dist' in workflow
    assert 'packages-dir: publish-dist/' in workflow
    assert 'packages-dir: ${{ runner.temp }}' not in workflow


@pytest.mark.parametrize('url', ['http://files.pythonhosted.org/x/a.whl','https://evil.example/a.whl','https://files.pythonhosted.org/x/a.whl?bad=1','https://files.pythonhosted.org/x/b.whl'])
def test_public_download_rejects_unapproved_url(url):
    import download_release_021 as public_download
    with pytest.raises(ValueError): public_download.check_url(url, 'a.whl')


def test_public_download_requires_complete_fixed_release():
    import download_release_021 as public_download
    value,public=manifest(),public_state()
    public['info']={'version':'0.2.1'}
    with pytest.raises(ValueError): public_download.check_listing(value,public)
    public['releases']['0.2.1']=[{'filename':r['file'],'size':r['bytes'],'digests':{'sha256':r['sha256']}} for r in value['files']]
    assert len(public_download.check_listing(value,public))==17


def test_captured_job_logs_allow_and_strip_ansi_without_terminal_rendering(monkeypatch):
    calls=[]
    def capture(args, **kwargs):
        calls.append(args)
        return b'\x1b[31mFINAL_RELEASE_CELL_OK {"result":"passed"}\x1b[0m\n'
    monkeypatch.setattr(guard.subprocess,'check_output',capture)
    result=guard.captured_job_log(123)
    assert '--allow-escape-sequences' in calls[0]
    assert '\x1b' not in result
    assert json.loads(result.split('FINAL_RELEASE_CELL_OK ',1)[1])['result']=='passed'


def test_recovery_pins_successful_qualification_source():
    assert guard.QUALIFICATION_SOURCE_REVISION=='f5fdc6d35250d8466b05da682cb0aefc85ae5e72'


def test_production_verifier_uses_immutable_version_endpoints(monkeypatch):
    import io
    import download_release_021 as download
    calls=[]
    def open_json(request, **kwargs):
        calls.append(request.full_url)
        version=request.full_url.split('/')[-2]
        assert version in ('0.2.0','0.2.1')
        return io.BytesIO(json.dumps({'info':{'name':'gmatpy','version':version},'urls':[]}).encode())
    monkeypatch.setattr(download.urllib.request,'urlopen',open_json)
    snapshot=download.public_snapshot()
    assert snapshot['info']['version']=='0.2.1'
    assert set(snapshot['releases'])=={'0.2.0','0.2.1'}
    assert calls==['https://pypi.org/pypi/gmatpy/0.2.0/json','https://pypi.org/pypi/gmatpy/0.2.1/json']
