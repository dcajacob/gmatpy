"""Bounded negative checks for release inventory, path and RECORD controls."""
import base64
import copy
import csv
import hashlib
import io

import pytest

from release_bundle import check_manifest
from reuse_wheels import load_inputs, safe_names, verify_record


def manifest():
    inputs = load_inputs()
    files = [{'file': r['file'].replace('0.2.1.dev0', '0.2.1'), 'sha256': r['sha256'],
              'bytes': r['bytes'], 'minor': r['minor'], 'target': r['target']} for r in inputs['files']]
    files.append({'file': 'gmatpy-0.2.1.tar.gz', 'sha256': 'a' * 64, 'bytes': 74_000_000})
    return {'schema_version': 1, 'project': 'gmatpy', 'version': '0.2.1',
            'native_build_source_revision': inputs['source']['source_revision'], 'native_recompiled': False,
            'packaging_source': {'source_archive': 'gmatpy-0.2.1.tar.gz'}, 'files': files}


def test_accept_complete_qualified_inventory():
    assert len(check_manifest(manifest())) == 16


@pytest.mark.parametrize('field,value', [('version', '0.2.0'), ('version', '0.2.1.dev0'),
                                        ('project', 'other'), ('native_recompiled', True),
                                        ('native_build_source_revision', 'a' * 40), ('schema_version', 2)])
def test_reject_wrong_release_identity(field, value):
    value_manifest = manifest()
    value_manifest[field] = value
    with pytest.raises(ValueError):
        check_manifest(value_manifest)


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'extra', 'target', 'minor', 'name',
                                   'path', 'hash', 'size', 'source'])
def test_reject_unqualified_or_malformed_file(change):
    value = manifest()
    if change == 'missing': value['files'].pop()
    if change == 'duplicate': value['files'][1] = copy.deepcopy(value['files'][0])
    if change == 'extra': value['files'].append(copy.deepcopy(value['files'][0]))
    if change == 'target': value['files'][0]['target'] = 'windows-x86_64'
    if change == 'minor': value['files'][0]['minor'] = '3.16'
    if change == 'name': value['files'][0]['file'] = value['files'][0]['file'].replace('cp313', 'cp313t')
    if change == 'path': value['files'][0]['file'] = '../' + value['files'][0]['file']
    if change == 'hash': value['files'][0]['sha256'] = 'z' * 64
    if change == 'size': value['files'][0]['bytes'] = 100_000_000
    if change == 'source': value['packaging_source']['source_archive'] = 'wrong.tar.gz'
    with pytest.raises(ValueError):
        check_manifest(value)


@pytest.mark.parametrize('names', [['a', 'a'], ['../a'], ['/a'], ['a/../b'], ['a//b']])
def test_reject_unsafe_names(names):
    with pytest.raises(ValueError):
        safe_names(names)


def record_fixture():
    data = b'qualified payload'
    value = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(['gmatpy/data', 'sha256=' + value, len(data)])
    writer.writerow(['gmatpy-0.2.1.dist-info/RECORD', '', ''])
    return {'gmatpy/data': data, 'gmatpy-0.2.1.dist-info/RECORD': stream.getvalue().encode()}


def test_accept_complete_record():
    verify_record(record_fixture())


@pytest.mark.parametrize('change', ['bytes', 'missing', 'extra', 'duplicate', 'size', 'self'])
def test_reject_record_tampering(change):
    payload = record_fixture()
    record = 'gmatpy-0.2.1.dist-info/RECORD'
    if change == 'bytes': payload['gmatpy/data'] += b'bad'
    if change == 'missing': del payload['gmatpy/data']
    if change == 'extra': payload['other'] = b'extra'
    if change == 'duplicate': payload[record] += payload[record].splitlines(keepends=True)[0]
    if change == 'size': payload[record] = payload[record].replace(b',17\n', b',18\n')
    if change == 'self': payload[record] = payload[record].replace(b'RECORD,,', b'RECORD,sha256=bad,1')
    with pytest.raises(ValueError):
        verify_record(payload)
