"""Publish only four immutable qualified Windows additions to existing 0.2.1.

No build, repair, metadata rewrite or file replacement. Existing production
hashes, qualification run, artifact digests and source compatibility are fixed.
Uses the existing publish-pypi.yml / protected pypi Trusted Publisher only.
"""
import argparse
from collections import defaultdict
import email.parser
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'python/tools'))
from check_distribution import check, export_scope_files
from record_source import source_files

CONFIG = ROOT/'.github/release/pypi-0.2.1-windows.json'
CONFIG_SHA256 = 'd35a44e6a993964b7891956ac952cf9d8745ddc20927adc6b2a05d5edfb64066'
REPOSITORY = 'dcajacob/gmatpy'
VERSIONS = ('3.12.10', '3.13.16', '3.14.8', '3.15.0')


def require(value, message):
    if not value: raise ValueError(message)


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def load_config():
    require(sha(CONFIG)==CONFIG_SHA256,'Windows allowlist changed')
    m=json.loads(CONFIG.read_text())
    require(m['project']=='gmatpy' and m['version']=='0.2.1' and len(m['files'])==4,'Unexpected release')
    require({f['python'] for f in m['files']}==set(VERSIONS),'Unexpected ABI inventory')
    original=ROOT/'.github/release/pypi-0.2.1.json'
    require(sha(original)=='738697d00a2b1daa5ddba13ae7b30c1f26a6ddad8bbcf37ea5491b840319a8d6','Original release allowlist changed')
    baseline=json.loads(original.read_text())
    require(m['preserve']['0.2.1']=={r['file']:{'sha256':r['sha256'],'bytes':r['bytes']} for r in baseline['files']},'Original 0.2.1 preservation differs')
    require({n:r['sha256'] for n,r in m['preserve']['0.2.0'].items()}==baseline['preserve_production_020'],'Original 0.2.0 preservation differs')
    for f in m['files']:
        tag='cp'+''.join(f['python'].split('.')[:2])
        require(f['wheel']==f'gmatpy-0.2.1-{tag}-{tag}-win_amd64.whl','Unexpected wheel name')
    return m


def api(path):
    return json.loads(subprocess.check_output(['gh','api',path],timeout=90))


def public_snapshot():
    result={}
    for version in ('0.2.0','0.2.1'):
        request=urllib.request.Request(f'https://pypi.org/pypi/gmatpy/{version}/json',headers={'Cache-Control':'no-cache'})
        with urllib.request.urlopen(request,timeout=60) as response: result[version]=json.load(response)
        require(result[version]['info']['name']=='gmatpy' and result[version]['info']['version']==version,'Wrong PyPI project/version')
    return result


def check_public_state(m, public, complete=False):
    additions={f['wheel']:f for f in m['files']};present=set()
    for version, baseline in m['preserve'].items():
        files=public[version]['urls'];actual={f['filename']:f for f in files}
        require(len(actual)==len(files),'Duplicate public filenames')
        allowed=dict(baseline)
        if version=='0.2.1':allowed.update(additions)
        require(set(baseline)<=set(actual) and set(actual)<=set(allowed),'Existing files missing or unknown public file')
        for name,f in actual.items():
            expected=allowed[name]
            require(f['size']==expected['bytes'] and f['digests']['sha256']==expected['sha256'] and not f.get('yanked'),'Existing PyPI file conflicts; never replace')
            if name in additions:present.add(name)
    if complete:require(present==set(additions),'Windows publication incomplete')
    return present


def download_public_source(m, public, output):
    f=next(f for f in public['0.2.1']['urls'] if f['filename']=='gmatpy-0.2.1.tar.gz')
    url=urllib.parse.urlsplit(f['url'])
    require(url.scheme=='https' and url.netloc=='files.pythonhosted.org' and not url.query and not url.fragment,'Unexpected PyPI file URL')
    with urllib.request.urlopen(f['url'],timeout=120) as stream,output.open('xb') as target:shutil.copyfileobj(stream,target)
    expected=m['preserve']['0.2.1']['gmatpy-0.2.1.tar.gz']
    require(output.stat().st_size==expected['bytes'] and sha(output)==expected['sha256'],'Published source bytes differ')


def download_artifact(m, record, directory):
    actual=api(f'repos/{REPOSITORY}/actions/artifacts/{record["id"]}')
    require(all(actual[k]==record[k] for k in ('id','name','size_in_bytes','digest')) and not actual['expired'],'Artifact identity/retention differs')
    require(actual['workflow_run']['id']==m['qualification_run'] and actual['workflow_run']['head_sha']==m['qualification_source'],'Artifact source differs')
    require(0<record['size_in_bytes']<=90_000_000,'Artifact storage bound exceeded')
    directory.mkdir()
    archive=directory/'payload.zip'
    with archive.open('xb') as stream:
        subprocess.run(['gh','api',f'repos/{REPOSITORY}/actions/artifacts/{record["id"]}/zip'],stdout=stream,check=True,timeout=240)
    require(archive.stat().st_size==record['size_in_bytes'] and record['digest']=='sha256:'+sha(archive),'Artifact ZIP digest differs')
    output=directory/'files';output.mkdir()
    with zipfile.ZipFile(archive) as z:
        names=z.namelist();require(len(names)==len(set(names)),'Duplicate artifact paths')
        for entry in z.infolist():
            p=Path(entry.filename)
            require(not p.is_absolute() and '..' not in p.parts and '\\' not in entry.filename and
                    not ((entry.external_attr>>16)&0o170000)==0o120000 and entry.file_size<=90_000_000,'Unsafe artifact member')
        require(sum(i.file_size for i in z.infolist())<=90_000_000,'Artifact expanded storage bound exceeded')
        z.extractall(output)
    return output


def verify_run(m):
    run=api(f'repos/{REPOSITORY}/actions/runs/{m["qualification_run"]}')
    require(run['repository']['full_name']==REPOSITORY and run['event']=='push' and
            run['head_sha']==m['qualification_source'] and run['head_branch']==m['qualification_branch'] and
            run['path']==m['qualification_workflow'] and run['run_attempt']==1 and
            run['status']=='completed' and run['conclusion']=='success','Qualification run differs')
    jobs=api(f'repos/{REPOSITORY}/actions/runs/{m["qualification_run"]}/jobs?per_page=100')['jobs']
    expected={'source','primary314 / qualify','assess (3.12.10) / qualify','assess (3.13.16) / qualify','assess (3.15.0) / qualify'}
    require(len(jobs)==5 and {j['name'] for j in jobs}==expected and all(j['status']=='completed' and j['conclusion']=='success' for j in jobs),'Native qualification incomplete')


def verify_source_compatibility(published, candidate, m):
    proof_file=ROOT/'.github/release/windows-source-compatibility-0.2.1.json'
    require(sha(proof_file)==m['source_compatibility_sha256'],'Source compatibility receipt differs')
    proof=json.loads(proof_file.read_text())
    with tarfile.open(published) as t:
        old=source_files(t);metadata=t.extractfile('gmatpy-0.2.1/PKG-INFO').read()
    with tarfile.open(candidate) as t:
        new=source_files(t);provenance=t.extractfile('gmatpy-0.2.1/python/gmatpy/BUILD_PROVENANCE.json').read()
    a={f['path']:f for f in old};b={f['path']:f for f in new}
    changes=[{'path':n,'old':a.get(n),'new':b.get(n)} for n in sorted(set(a)|set(b)) if a.get(n)!=b.get(n)]
    require(export_scope_files(old)==export_scope_files(new),'Scientific/runtime/build source changed; reassess version')
    require(changes==proof['changed_source_records'],'Source differences exceed reviewed docs/CI/tests')
    require(sha(candidate)==m['source_receipt']['source_archive_sha256'],'Candidate source differs')
    return provenance,metadata


def verify_wheel(directory, record, m, provenance, published_metadata):
    wheel=directory/record['wheel']
    require(wheel.stat().st_size==record['bytes'] and sha(wheel)==record['sha256'],'Wheel differs from qualified bytes')
    result=json.loads((directory/'RESULTS.json').read_text());profile=result['profiles']['extended']
    require(result['target']=='windows-x86_64' and result['interpreter']['version']==record['python'] and
            result['release_preflight']=='passed' and result['source_tree_sha256']==m['source_receipt']['source_tree_sha256'] and
            result['sdist_sha256']==m['source_receipt']['source_archive_sha256'] and profile['sha256']==record['sha256'] and
            profile['wheel']==record['wheel'] and profile['bytes']==record['bytes'] and
            re.fullmatch(r'203 passed, 6 skipped, 3 subtests passed in [0-9.]+s',profile['tests']),'Qualification result differs')
    for name,digest in json.loads((directory/'EVIDENCE_SHA256.json').read_text()).items():
        normalized=name.replace('\\','/')
        file=directory/('spline-RESULTS.json' if normalized=='extended/spline/RESULTS.json' else Path(normalized).name)
        require(sha(file)==digest,'Qualification evidence changed')
    with zipfile.ZipFile(wheel) as z:
        require(z.read('gmatpy/BUILD_PROVENANCE.json')==provenance,'Embedded source provenance differs')
        native={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.endswith(('.dll','.pyd'))}
        require(native==record['native_members'],'Native members differ')
        parser=email.parser.BytesParser();a=parser.parsebytes(published_metadata);b=parser.parsebytes(z.read('gmatpy-0.2.1.dist-info/METADATA'))
        require(all(sorted(a.get_all(k,[]))==sorted(b.get_all(k,[])) for k in set(a)|set(b)),'Metadata identity/dependencies differ')
    check(wheel,release=True,source_manifest=directory/'SOURCE_PROVENANCE.json')
    return wheel


def context(env):
    expected={'GITHUB_REPOSITORY':REPOSITORY,'GITHUB_REF':'refs/heads/main','GITHUB_EVENT_NAME':'workflow_dispatch',
              'GITHUB_RUN_ATTEMPT':'1','GITHUB_WORKFLOW_REF':REPOSITORY+'/.github/workflows/publish-pypi.yml@refs/heads/main'}
    require(all(env.get(k)==v for k,v in expected.items()),'Unapproved publication context')


def prepare(m,temp,output):
    context(os.environ);verify_run(m)
    public=public_snapshot();present=check_public_state(m,public)
    temp.mkdir(exist_ok=False)
    source=download_artifact(m,m['source_artifact'],temp/'source')
    require(json.loads((source/'SOURCE_RECEIPT.json').read_text())==m['source_receipt'],'Frozen source receipt differs')
    require(sha(source/'WORKING_TREE.json')==m['source_receipt']['working_tree_manifest_sha256'],'Working tree receipt differs')
    published=temp/'published-source.tar.gz';download_public_source(m,public,published)
    provenance,metadata=verify_source_compatibility(published,source/'artifacts/gmatpy-0.2.1.tar.gz',m)
    output.mkdir(exist_ok=False)
    for i,record in enumerate(m['files']):
        directory=download_artifact(m,record['artifact'],temp/str(i))
        (directory/'SOURCE_PROVENANCE.json').write_bytes(provenance)
        wheel=verify_wheel(directory,record,m,provenance,metadata)
        if record['wheel'] not in present:shutil.copyfile(wheel,output/wheel.name)
    # Recheck immediately before OIDC publication; only missing exact names remain.
    require(check_public_state(m,public_snapshot())==present,'Public state changed during preparation; inspect before retry')
    with open(os.environ['GITHUB_OUTPUT'],'a') as stream:stream.write('has_files='+str(len(present)<4).lower()+'\n')
    print('WINDOWS_021_PUBLISH_READY',4-len(present),CONFIG_SHA256,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=('prepare','public-check'))
    parser.add_argument('--temporary',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args();m=load_config()
    if args.mode=='prepare':prepare(m,args.temporary,args.output)
    else:check_public_state(m,public_snapshot(),complete=True);print('WINDOWS_021_PUBLIC_HASHES_OK')
