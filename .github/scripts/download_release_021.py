"""Download only exact public 0.2.1 files for post-publication verification."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

import release_021 as guard


def check_listing(manifest, public):
    names = guard.check_public_state(manifest, public)
    expected = {r['file'] for r in manifest['files']}
    guard.require(names == expected and public['info']['version'] == '0.2.1', 'Production release is incomplete')
    return {r['filename']: r for r in public['releases']['0.2.1']}


def check_url(url, filename):
    p = urllib.parse.urlsplit(url)
    guard.require(p.scheme == 'https' and p.netloc == 'files.pythonhosted.org'
                  and not p.query and not p.fragment and p.path.endswith('/' + filename),
                  'Unapproved production file URL')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Unexpected production file redirect')


def public_snapshot():
    # Project-level JSON may remain cached for900seconds during a multi-file
    # upload. Immutable version endpoints identify the exact release instead.
    releases = {}
    info = None
    for version in ('0.2.0', '0.2.1'):
        request = urllib.request.Request(f'https://pypi.org/pypi/gmatpy/{version}/json',
                                         headers={'Cache-Control':'no-cache'})
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
        guard.require(result['info']['name']=='gmatpy' and result['info']['version']==version,
                      'Wrong production project/version endpoint')
        releases[version] = result['urls']
        if version == '0.2.1': info = result['info']
    return {'info':info,'releases':releases,
            'verification_api':'Version-specific0.2.0/0.2.1JSON;not a cached project snapshot'}


def download(target, destination):
    manifest = guard.load_config()
    public = public_snapshot()
    files = check_listing(manifest, public)
    destination.mkdir(exist_ok=False)
    opener = urllib.request.build_opener(NoRedirect())
    for record in manifest['files']:
        if target != 'all' and record['file'].endswith('.whl') and record['target'] != target:
            continue
        url = files[record['file']]['url']
        check_url(url, record['file'])
        path = destination / record['file']
        digest, total = hashlib.sha256(), 0
        with opener.open(url, timeout=120) as source, path.open('xb') as output:
            while chunk := source.read(1024 * 1024):
                total += len(chunk)
                guard.require(total <= record['bytes'], 'Production download exceeds fixed size')
                digest.update(chunk)
                output.write(chunk)
        guard.require(total == record['bytes'] and digest.hexdigest() == record['sha256'], 'Production bytes differ')
        print('PUBLIC_FILE_SHA256_OK', record['file'], digest.hexdigest(), flush=True)
    return public


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=('all', *guard.TARGETS), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    download(args.target, args.output)
