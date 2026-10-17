"""Deterministically repackage 0.2.1 with exact qualified f8 native byte reuse.

No compiler, repair command, network, Git mutation or upload is invoked here.
Original compilation and new packaging source identities remain separate.
"""
import argparse
import base64
import csv
import datetime
from email.parser import BytesParser
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile

NATIVE_SOURCE = 'f8d8e4ce997ca7400afbe035b7ec55bd66c02575'
VERSION = '0.2.1'
OLD_VERSION = '0.2.1.dev0'
RECEIPTS = ('RESULTS.json', 'INTERPRETER.json', 'CSPICE_BUILD_DEPENDENCY.json', 'SOURCE_RECEIPT.json')
SOURCE_CHANGES = {'pyproject.toml', 'python/gmatpy/__init__.py'}
PACKAGE_CHANGES = {'gmatpy/__init__.py', 'gmatpy/BUILD_PROVENANCE.json',
                   'gmatpy/licenses/CODE_MANIFEST.json', 'gmatpy/licenses/EXPORT_DETERMINATION.json'}
ORIGINAL_SOURCE_NAME = 'ORIGINAL_SOURCE_PROVENANCE.json'
REUSE_NAME = 'BINARY_REUSE_PROVENANCE.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def encoded(obj):
    return (json.dumps(obj, sort_keys=True, indent=2) + '\n').encode()


def load_inputs():
    result = json.loads(Path(__file__).with_name('reuse-inputs-0.2.1.json').read_text())
    require(result['source']['source_revision'] == NATIVE_SOURCE and len(result['files']) == 16,
            'Unexpected qualified input registry')
    return result


def safe_names(names):
    require(len(names) == len(set(names)), 'Duplicate archive member')
    for name in names:
        p = PurePosixPath(name)
        require(not p.is_absolute() and '..' not in p.parts and str(p) == name.rstrip('/'),
                'Unsafe archive member')


def verify_record(payload):
    safe_names(list(payload))
    record_names = [n for n in payload if n.endswith('.dist-info/RECORD')]
    require(len(record_names) == 1, 'Expected one RECORD')
    record = record_names[0]
    rows = list(csv.reader(io.StringIO(payload[record].decode())))
    require(len(rows) == len({row[0] for row in rows}) and {row[0] for row in rows} == set(payload),
            'RECORD inventory differs')
    for name, expected, size in rows:
        if name == record:
            require(expected == size == '', 'RECORD must not hash itself')
        else:
            data = payload[name]
            value = 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
            require(expected == value and size == str(len(data)), 'RECORD hash/size differs: ' + name)


def read_payload(path):
    with zipfile.ZipFile(path) as archive:
        safe_names(archive.namelist())
        require(not any(n.endswith(('.jws', '.p7s', '.sigstore')) for n in archive.namelist()),
                'Signed input must not be silently rewritten')
        payload = {n: archive.read(n) for n in archive.namelist() if not n.endswith('/')}
    verify_record(payload)
    return payload


def native_members(payload):
    return {n: {'sha256': digest(data), 'bytes': len(data)} for n, data in payload.items()
            if data[:4] in (b'\x7fELF', b'\xcf\xfa\xed\xfe')}


def check_scientific_successor(old, new, snapshot):
    sys.path.insert(0, str(snapshot / 'python/tools'))
    from check_distribution import export_scope_files
    before = {r['path']: r for r in export_scope_files(old['files'])}
    after = {r['path']: r for r in export_scope_files(new['files'])}
    require(before.keys() == after.keys() and len(before) == 1176, 'Scientific inventory changed')
    changed = {n for n in before if before[n] != after[n]}
    require(changed == SOURCE_CHANGES, 'Unexpected scientific/build/runtime source change')
    return sorted(changed)


def verify_reuse_payload(payload, entry, provenance):
    prefix = f'gmatpy-{VERSION}.dist-info/'
    require(payload['gmatpy/BUILD_PROVENANCE.json'] == provenance, 'Packaging provenance differs')
    metadata = BytesParser().parsebytes(payload[prefix + 'METADATA'])
    require(metadata['Name'] == 'gmatpy' and metadata['Version'] == VERSION,
            'Release metadata differs')
    require(set(metadata['Requires-Python'].split(',')) == {'>=3.12', '<3.16'}, 'Interpreter range differs')
    require(f'__version__ = "{VERSION}"'.encode() in payload['gmatpy/__init__.py'], 'Runtime version differs')
    require(native_members(payload) == entry['native_members'] and len(native_members(payload)) == 3,
            'Qualified native member bytes differ')
    require(digest(payload['gmatpy/_native/gmat_py.py']) == entry['swig_wrapper_sha256'], 'SWIG wrapper differs')
    reuse = json.loads(payload[prefix + REUSE_NAME])
    require(reuse['native_build_source_revision'] == NATIVE_SOURCE
            and reuse['native_recompiled'] is False
            and reuse['native_build_from_packaging_revision_claimed'] is False,
            'False native compilation origin')
    require(reuse['original_wheel_sha256'] == entry['sha256']
            and reuse['original_qualified_wheel'] == entry['file']
            and reuse['native_members'] == entry['native_members']
            and reuse['target'] == entry['target'] and reuse['minor'] == entry['minor'],
            'Original qualified wheel identity differs')
    current = json.loads(provenance)
    require(reuse['packaging_source_revision'] == current['source_revision']
            and reuse['packaging_source_manifest_sha256'] == digest(provenance), 'Reuse packaging source differs')
    original = json.loads(payload[prefix + ORIGINAL_SOURCE_NAME])
    require(original['source_revision'] == NATIVE_SOURCE
            and original['source_tree_sha256'] == load_inputs()['source']['source_tree_sha256'],
            'Original source differs')
    for name, expected in entry['receipts_sha256'].items():
        data = payload[prefix + 'ORIGINAL_' + name]
        require(digest(data) == expected, 'Original qualification/dependency receipt differs')
    result = json.loads(payload[prefix + 'ORIGINAL_RESULTS.json'])
    require(result['source_tree_sha256'] == load_inputs()['source']['source_tree_sha256']
            and result['sdist_sha256'] == load_inputs()['source']['source_archive_sha256']
            and result['target'] == entry['target']
            and result['python_minor'] == entry['minor'] and result['release_preflight'] == 'passed',
            'Original qualification source/cell differs')
    old_metadata = BytesParser().parsebytes(payload[prefix + 'WHEEL'])
    require(old_metadata.get_all('Build') is None, 'Unexpected wheel build tag')
    tags = set(old_metadata.get_all('Tag', []))
    parts = entry['file'].removesuffix('.whl').split('-')
    expected_tags = {f'{parts[2]}-{parts[3]}-{p}' for p in parts[4].split('.')}
    require(tags == expected_tags, 'Qualified ABI/platform tags differ')
    verify_record(payload)
    return reuse


def repackage(original_dir, receipts_dir, frozen, output):
    inputs = load_inputs()
    source_receipt = json.loads((frozen / 'SOURCE_RECEIPT.json').read_text())
    snapshot = frozen / 'snapshot' / f'gmatpy-{VERSION}'
    provenance = (snapshot / 'python/gmatpy/BUILD_PROVENANCE.json').read_bytes()
    new_source = json.loads(provenance)
    require(new_source['source_revision'] == source_receipt['source_revision'], 'Frozen source identity differs')
    output.mkdir(exist_ok=False)
    rows = []
    for entry in inputs['files']:
        path = original_dir / entry['file']
        require(sha(path) == entry['sha256'] and path.stat().st_size == entry['bytes'], 'Input archive differs')
        old = read_payload(path)
        require(native_members(old) == entry['native_members'], 'Input native library differs')
        original_provenance = old['gmatpy/BUILD_PROVENANCE.json']
        previous_source = json.loads(original_provenance)
        require(previous_source['source_revision'] == NATIVE_SOURCE, 'Input native source differs')
        changes = check_scientific_successor(previous_source, new_source, snapshot)
        for name in SOURCE_CHANGES:
            record = next(r for r in previous_source['files'] if r['path'] == name)
            prior = (snapshot / name).read_bytes().replace(VERSION.encode(), OLD_VERSION.encode(), 1)
            require(digest(prior) == record['sha256'], 'Source change exceeds version-only replacement')
        old_prefix = f'gmatpy-{OLD_VERSION}.dist-info/'
        prefix = f'gmatpy-{VERSION}.dist-info/'
        payload = {n.replace(old_prefix, prefix, 1): data for n, data in old.items()}
        for name in PACKAGE_CHANGES - {'gmatpy/BUILD_PROVENANCE.json'}:
            payload[name] = (snapshot / 'python' / name).read_bytes()
        payload['gmatpy/BUILD_PROVENANCE.json'] = provenance
        payload[prefix + 'METADATA'] = (snapshot / 'PKG-INFO').read_bytes()
        wheel_meta = BytesParser().parsebytes(payload[prefix + 'WHEEL'])
        generator = wheel_meta['Generator']
        wheel_meta.replace_header('Generator', 'gmatpy-qualified-binary-reuse 0.2.1')
        payload[prefix + 'WHEEL'] = wheel_meta.as_bytes()
        folder = receipts_dir / f"candidate-{entry['minor']}-{entry['target']}-{NATIVE_SOURCE}"
        for name, expected in entry['receipts_sha256'].items():
            data = (folder / name).read_bytes()
            require(digest(data) == expected, 'Input qualification receipt differs')
            payload[prefix + 'ORIGINAL_' + name] = data
        payload[prefix + ORIGINAL_SOURCE_NAME] = original_provenance
        reuse = {'schema_version': 1, 'operation': 'version_metadata_repackage_with_qualified_native_reuse',
                 'packaging_source_revision': new_source['source_revision'],
                 'packaging_source_manifest_sha256': digest(provenance),
                 'native_build_source_revision': NATIVE_SOURCE, 'native_recompiled': False,
                 'native_build_from_packaging_revision_claimed': False,
                 'original_qualified_wheel': entry['file'], 'original_wheel_sha256': entry['sha256'],
                 'original_native_source_manifest_sha256': digest(original_provenance),
                 'original_wheel_generator': generator, 'minor': entry['minor'], 'target': entry['target'],
                 'native_members': entry['native_members'], 'swig_wrapper_sha256': entry['swig_wrapper_sha256'],
                 'recipe_sha256': sha(Path(__file__)), 'scientific_scope_changed_paths': changes,
                 'qualification_run': entry['qualification_run'],
                 'original_qualification_is_carried_forward': True,
                 'new_installed_release_validation_required': True,
                 'receipts_sha256': entry['receipts_sha256']}
        payload[prefix + REUSE_NAME] = encoded(reuse)
        record_name = prefix + 'RECORD'
        stream = io.StringIO(newline='')
        writer = csv.writer(stream, lineterminator='\n')
        for name, data in sorted(payload.items()):
            if name != record_name:
                writer.writerow([name, 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode(), len(data)])
        writer.writerow([record_name, '', ''])
        payload[record_name] = stream.getvalue().encode()
        allowed = PACKAGE_CHANGES | {prefix + n for n in ('METADATA', 'WHEEL', 'RECORD', REUSE_NAME, ORIGINAL_SOURCE_NAME)}
        allowed |= {prefix + 'ORIGINAL_' + n for n in RECEIPTS}
        mapped_old = {n.replace(old_prefix, prefix, 1): data for n, data in old.items()}
        changed = {n for n in payload if payload[n] != mapped_old.get(n)}
        require(changed == allowed, 'Unexpected wheel member change')
        verify_reuse_payload(payload, entry, provenance)
        destination = output / entry['file'].replace(OLD_VERSION, VERSION)
        timestamp = datetime.datetime.fromtimestamp(int(source_receipt['source_date_epoch']), datetime.timezone.utc)
        with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name, data in sorted(payload.items()):
                info = zipfile.ZipInfo(name, timestamp.timetuple()[:6])
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o100755 if name in entry['native_members'] else 0o100644) << 16
                archive.writestr(info, data, compresslevel=6)
        verify_reuse_payload(read_payload(destination), entry, provenance)
        rows.append({'file': destination.name, 'sha256': sha(destination), 'bytes': destination.stat().st_size,
                     'minor': entry['minor'], 'target': entry['target'], 'original_file': entry['file'],
                     'original_sha256': entry['sha256'], 'native_members': entry['native_members'],
                     'changed_members': sorted(changed)})
        print('REPACKED_NATIVE_BYTES_UNCHANGED', destination.name, rows[-1]['sha256'], flush=True)
    manifest = {'schema_version': 1, 'project': 'gmatpy', 'version': VERSION,
                'packaging_source': source_receipt, 'native_build_source_revision': NATIVE_SOURCE,
                'native_recompiled': False, 'new_installed_validation_required': True, 'files': rows}
    (output.parent / 'REPACKED.json').write_bytes(encoded(manifest))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original-dir', 'receipts-dir', 'frozen', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    repackage(args.original_dir, args.receipts_dir, args.frozen, args.output)
