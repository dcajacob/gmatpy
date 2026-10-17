"""Retain a verified candidate wheel and receipts under one fixed payload cap."""
import argparse,hashlib,json,shutil
from pathlib import Path
from check_frozen_input import check


def collect(root, source, revision, output):
    receipt=check(source,revision)
    result=json.loads((root/'qualified/RESULTS.json').read_text())
    assert result['release_preflight']=='passed'
    assert result['sdist_sha256']==receipt['source_archive_sha256']
    assert result['source_tree_sha256']==receipt['source_tree_sha256']
    profile=result['profiles']['extended']
    assert 'passed' in profile['tests'] and 'failed' not in profile['tests']
    assert Path(profile['wheel']).name==profile['wheel']
    wheel=root/'qualified/extended/wheelhouse'/profile['wheel']
    assert wheel.stat().st_size==profile['bytes']
    with wheel.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==profile['sha256']
    logs=[root/'qualified/extended'/n for n in ['pytest.log','installed-bytes.log','binary-contents-check.log','release-preflight.log','state-comparison.json']]
    files=[*logs,wheel,root/'qualified/RESULTS.json',root/'qualified/EVIDENCE_SHA256.json',root/'qualified/CSPICE_BUILD_DEPENDENCY.json',root/'interpreter/INTERPRETER.json',source/'SOURCE_RECEIPT.json']
    assert len({f.name for f in files})==len(files)
    assert sum(f.stat().st_size for f in files)<=90000000
    output.mkdir(parents=True,exist_ok=False)
    for file in files:shutil.copy2(file,output/file.name)
    print(json.dumps({'candidate_only':True,'source_revision':revision,'target':result['target'],'python_minor':result['python_minor'],'wheel':profile['wheel'],'sha256':profile['sha256'],'tests':profile['tests'],'retained_bytes':sum(f.stat().st_size for f in output.iterdir())}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('root','source','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--revision',required=True);a=p.parse_args();collect(a.root,a.source,a.revision,a.output)
