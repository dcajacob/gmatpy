"""Fixed-file staging/publication guards for 0.2.1; no build or repack commands.

Network operations occur only in explicit stage/prepare modes after dispatch.
The local verify mode is read-only apart from temporary extracted metadata.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python/ci'))
from reuse_wheels import encoded, require, safe_names, sha
from release_bundle import CAP, TARGETS, MINORS, check_manifest, verify_bundle

REPOSITORY = 'dcajacob/gmatpy'
CONFIG = Path('.github/release/pypi-0.2.1.json')
CONFIG_SHA256 = '738697d00a2b1daa5ddba13ae7b30c1f26a6ddad8bbcf37ea5491b840319a8d6'
QUALIFICATION_WORKFLOW = '.github/workflows/qualify-release-0.2.1.yml'
# Immutable successful qualification; subsequent publisher-only fixes cannot
# relabel its source or justify rebuilding/restaging the sealed payload.
QUALIFICATION_SOURCE_REVISION = 'f5fdc6d35250d8466b05da682cb0aefc85ae5e72'


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', path], timeout=60))


def context(environment, workflow):
    expected = {'GITHUB_REPOSITORY': REPOSITORY, 'GITHUB_REF': 'refs/heads/main',
                'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_RUN_ATTEMPT': '1',
                'GITHUB_WORKFLOW_REF': f'{REPOSITORY}/.github/workflows/{workflow}@refs/heads/main'}
    require(all(environment.get(k) == v for k, v in expected.items()), 'Unapproved workflow context')
    require(re.fullmatch('[0-9a-f]{40}', environment.get('GITHUB_SHA', '')), 'Missing immutable control source')


def load_config():
    require(sha(CONFIG) == CONFIG_SHA256, 'Release allowlist changed')
    manifest = json.loads(CONFIG.read_text())
    check_manifest(manifest)
    return manifest


def stage(manifest, output, release_id):
    context(os.environ, 'qualify-release-0.2.1.yml')
    require(re.fullmatch('[1-9][0-9]*', release_id), 'Invalid staging draft ID')
    release = api(f'repos/{REPOSITORY}/releases/{release_id}')
    revision = manifest['packaging_source']['source_revision']
    require(release['draft'] is True and release['tag_name'] == f'staging-gmatpy-0.2.1-{revision[:12]}'
            and release['target_commitish'] == revision, 'Unexpected draft/source identity')
    records = {r['file']: r for r in manifest['files']}
    assets = release['assets']
    require(len(assets) == 17 and {a['name'] for a in assets} == set(records), 'Draft asset inventory differs')
    output.mkdir(exist_ok=False)
    for asset in assets:
        record = records[asset['name']]
        require(asset['state'] == 'uploaded' and asset['size'] == record['bytes'], 'Draft asset size/state differs')
        if asset.get('digest'):
            require(asset['digest'] == 'sha256:' + record['sha256'], 'Draft service hash differs')
        path = output / record['file']
        with path.open('xb') as stream:
            subprocess.run(['gh', 'api', '-H', 'Accept: application/octet-stream',
                            f'repos/{REPOSITORY}/releases/assets/{asset["id"]}'],
                           stdout=stream, check=True, timeout=180)
        require(path.stat().st_size == record['bytes'] and sha(path) == record['sha256'], 'Draft bytes differ')
    verify_bundle(output, manifest)
    print('STAGING_17_FILES_VERIFIED', CONFIG_SHA256, flush=True)


def verify_qualification(run, jobs, control_revision):
    require(run['repository']['full_name'] == REPOSITORY and run['event'] == 'workflow_dispatch'
            and run['head_sha'] == control_revision and run['head_branch'] == 'main'
            and run['path'] == QUALIFICATION_WORKFLOW and run['run_attempt'] == 1
            and run['status'] == 'completed' and run['conclusion'] == 'success',
            'Qualification run identity/conclusion differs')
    expected = {'stage'} | {f'installed ({target})' for target in TARGETS}
    require(len(jobs) == len(expected) and {j['name'] for j in jobs} == expected
            and all(j['status'] == 'completed' and j['conclusion'] == 'success' for j in jobs),
            'Not all native final-wheel jobs passed')


def verify_cell_records(records, manifest):
    require(len(records) == 16, 'Expected sixteen final-wheel results')
    by_cell = {(r['minor'], r['target']): r for r in records}
    require(len(by_cell) == 16 and set(by_cell) == {(m, t) for m in MINORS for t in TARGETS},
            'Duplicate or missing installed-wheel cell')
    expected = {(r['minor'], r['target']): r for r in manifest['files'] if r['file'].endswith('.whl')}
    interpreters = json.loads((Path(__file__).resolve().parents[2] / 'python/ci/interpreters.json').read_text())['interpreters']
    for cell, result in by_cell.items():
        require(result['result'] == 'passed' and result['installed_bytes_and_versions'] == 'passed'
                and result['binary_check'] == 'passed' and result['version'] == '0.2.1'
                and result['packaging_source_revision'] == manifest['packaging_source']['source_revision']
                and result['native_build_source_revision'] == manifest['native_build_source_revision']
                and result['native_recompiled'] is False and result['wheel'] == expected[cell]
                and result['interpreter_version'] == interpreters['/'.join(cell)]['version'],
                'Final installed-wheel result differs from exact release')
        tests = result['tests']
        require(re.search(r'\b209 passed\b', tests) and re.search(r'\b3 subtests passed\b', tests)
                and not re.search(r'\b(?:failed|skipped|error)\b', tests), 'Incomplete installed test outcome')


def extract_bundle(archive, destination, manifest):
    records = {r['file']: r for r in manifest['files']}
    require(archive.stat().st_size <= CAP, 'Actions archive exceeds storage cap')
    with zipfile.ZipFile(archive) as zipped:
        safe_names(zipped.namelist())
        require(set(zipped.namelist()) == set(records), 'Actions archive inventory differs')
        for info in zipped.infolist():
            require(info.file_size == records[info.filename]['bytes'] and not info.is_dir()
                    and (info.external_attr >> 16) & 0o170000 != 0o120000, 'Invalid Actions member type/size')
        destination.mkdir(exist_ok=False)
        for name in records:
            with zipped.open(name) as source, (destination / name).open('xb') as target:
                shutil.copyfileobj(source, target)
    verify_bundle(destination, manifest)


def check_public_state(manifest, public):
    expected020 = manifest['preserve_production_020']
    actual020 = {f['filename']: f['digests']['sha256'] for f in public['releases'].get('0.2.0', [])}
    require(actual020 == expected020, 'Existing production 0.2.0 differs')
    records = {r['file']: r for r in manifest['files']}
    existing = public['releases'].get('0.2.1', [])
    require(len(existing) == len({f['filename'] for f in existing}), 'Duplicate existing PyPI files')
    for file in existing:
        require(file['filename'] in records and file['digests']['sha256'] == records[file['filename']]['sha256']
                and file['size'] == records[file['filename']]['bytes'] and not file.get('yanked'),
                'Existing 0.2.1 file conflicts; stop rather than overwrite')
    return {f['filename'] for f in existing}


def captured_job_log(job_id):
    # Opt in only for captured PIPE bytes, never terminal rendering. New gh
    # versions otherwise reject ANSI-bearing job logs before verification.
    raw = subprocess.check_output(['gh', 'api', '--allow-escape-sequences',
                                   f'repos/{REPOSITORY}/actions/jobs/{job_id}/logs'], timeout=120)
    return re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', raw.decode('utf-8-sig'))


def prepare_publish(manifest, run_id, temp, output):
    context(os.environ, 'publish-pypi.yml')
    require(re.fullmatch('[1-9][0-9]*', run_id), 'Invalid qualification run ID')
    run = api(f'repos/{REPOSITORY}/actions/runs/{run_id}')
    jobs = api(f'repos/{REPOSITORY}/actions/runs/{run_id}/jobs?per_page=100')['jobs']
    verify_qualification(run, jobs, QUALIFICATION_SOURCE_REVISION)
    records = []
    for job in jobs:
        if job['name'].startswith('installed ('):
            log = captured_job_log(job['id'])
            for line in log.splitlines():
                marker = 'FINAL_RELEASE_CELL_OK '
                if marker in line:
                    records.append(json.loads(line.split(marker, 1)[1]))
    verify_cell_records(records, manifest)
    artifacts = api(f'repos/{REPOSITORY}/actions/runs/{run_id}/artifacts?per_page=100')['artifacts']
    require(len(artifacts) == 1, 'Expected one fixed candidate bundle')
    artifact = artifacts[0]
    require(artifact['name'] == 'gmatpy-0.2.1-' + manifest['packaging_source']['source_revision'][:12]
            and not artifact['expired'] and 0 < artifact['size_in_bytes'] <= CAP,
            'Unapproved Actions artifact')
    temp.mkdir(exist_ok=False)
    archive = temp / 'candidate.zip'
    with archive.open('xb') as stream:
        subprocess.run(['gh', 'api', f'repos/{REPOSITORY}/actions/artifacts/{artifact["id"]}/zip'],
                       stdout=stream, check=True, timeout=300)
    require(archive.stat().st_size == artifact['size_in_bytes']
            and artifact['digest'] == 'sha256:' + sha(archive), 'Actions service/archive hash differs')
    extract_bundle(archive, temp / 'verified', manifest)
    request = urllib.request.Request('https://pypi.org/pypi/gmatpy/json', headers={'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=30) as response:
        public = json.load(response)
    existing = check_public_state(manifest, public)
    output.mkdir(exist_ok=False)
    for record in manifest['files']:
        if record['file'] not in existing:
            shutil.copyfile(temp / 'verified' / record['file'], output / record['file'])
    missing = len(manifest['files']) - len(existing)
    with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
        stream.write(f'has_files={str(missing > 0).lower()}\n')
    print('PUBLISH_READY_EXACT_FILES', missing, CONFIG_SHA256, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('verify', 'stage', 'prepare'))
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--temporary', type=Path)
    parser.add_argument('--release-id')
    parser.add_argument('--run-id')
    args = parser.parse_args()
    manifest = load_config()
    if args.mode == 'verify': verify_bundle(args.bundle, manifest)
    elif args.mode == 'stage': stage(manifest, args.output, args.release_id)
    else: prepare_publish(manifest, args.run_id, args.temporary, args.output)
