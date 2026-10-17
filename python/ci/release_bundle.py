"""Validate the complete immutable 0.2.1 release bundle; never build or upload."""
import argparse
import itertools
import json
from pathlib import Path
import sys
import tarfile

from reuse_wheels import VERSION, NATIVE_SOURCE, load_inputs, read_payload, require, sha, verify_reuse_payload

CAP = 1_532_000_000
TARGETS = ('linux-x86_64', 'linux-arm64', 'macos-arm64', 'macos-x86_64')
MINORS = ('3.12', '3.13', '3.14', '3.15')


def check_manifest(manifest):
    require(manifest.get('schema_version') == 1 and manifest.get('project') == 'gmatpy'
            and manifest.get('version') == VERSION and manifest.get('native_recompiled') is False
            and manifest.get('native_build_source_revision') == NATIVE_SOURCE,
            'Unapproved release identity')
    records = manifest['files']
    require(len(records) == 17 and len({r['file'] for r in records}) == 17, 'Expected exactly seventeen files')
    cells = {(r.get('minor'), r.get('target')) for r in records if r['file'].endswith('.whl')}
    require(cells == set(itertools.product(MINORS, TARGETS)), 'Release cell inventory differs')
    inputs = load_inputs()
    originals = {r['file'].replace(inputs['version'], VERSION): r for r in inputs['files']}
    for record in records:
        name = record['file']
        require(Path(name).name == name and 0 < record['bytes'] < 90_000_000
                and len(record['sha256']) == 64 and all(c in '0123456789abcdef' for c in record['sha256']),
                'Invalid release filename/hash/size')
        if name.endswith('.whl'):
            require(name in originals and (record['minor'], record['target']) ==
                    (originals[name]['minor'], originals[name]['target']), 'Unqualified wheel filename/cell')
        else:
            require(name == f'gmatpy-{VERSION}.tar.gz', 'Unexpected non-wheel distribution')
    require(sum(r['bytes'] for r in records) <= CAP, 'Release exceeds aggregate payload cap')
    require(manifest['packaging_source']['source_archive'] == f'gmatpy-{VERSION}.tar.gz', 'Source archive differs')
    return originals


def verify_bundle(directory, manifest, tools=None):
    originals = check_manifest(manifest)
    require({p.name for p in directory.iterdir()} == {r['file'] for r in manifest['files']},
            'Bundle contains unexpected or missing files')
    for record in manifest['files']:
        path = directory / record['file']
        require(path.is_file() and not path.is_symlink() and path.stat().st_size == record['bytes']
                and sha(path) == record['sha256'], 'Distribution differs from frozen release allowlist')
    source = directory / f'gmatpy-{VERSION}.tar.gz'
    require(sha(source) == manifest['packaging_source']['source_archive_sha256'], 'Source receipt hash differs')
    with tarfile.open(source) as archive:
        prefix = f'gmatpy-{VERSION}/'
        provenance = archive.extractfile(prefix + 'python/gmatpy/BUILD_PROVENANCE.json').read()
    identity = json.loads(provenance)
    for key in ('source_revision', 'source_tree_sha256', 'working_tree_manifest_sha256'):
        require(identity[key] == manifest['packaging_source'][key], 'Source identity differs')
    if tools is None:
        tools = Path(__file__).resolve().parents[1] / 'tools'
    sys.path.insert(0, str(tools))
    from check_distribution import check
    import tempfile
    with tempfile.TemporaryDirectory() as temp:
        expected = Path(temp) / 'BUILD_PROVENANCE.json'
        expected.write_bytes(provenance)
        check(source, release=True, source_manifest=expected)
        for record in manifest['files']:
            if record['file'].endswith('.whl'):
                path = directory / record['file']
                verify_reuse_payload(read_payload(path), originals[record['file']], provenance)
                check(path, release=True, source_manifest=expected)
    return provenance


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    verify_bundle(args.bundle, manifest)
    print('RELEASE_BUNDLE_OK: 17 exact files;48 native member instances;strict source/data/notices/reuse checks')
