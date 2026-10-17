"""Freeze an immutable clean Git checkout to a provenance-bound source archive.

Outputs stay outside the checkout. Dirty checkouts and stale generated source
provenance are rejected; packaging inputs are checked against committed bytes.
"""
import argparse,hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def freeze(repo,output,expected):
    repo=repo.resolve();output=output.resolve()
    if output.is_relative_to(repo):raise ValueError('Output must be outside checkout')
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0',PYTHONDONTWRITEBYTECODE='1')
    env.pop('PYTHONPATH',None)
    def git(*args):return subprocess.check_output(['git',*args],cwd=repo,env=env)
    revision=git('rev-parse','HEAD').decode().strip()
    if revision!=expected:raise ValueError('Checkout differs from requested immutable commit')
    if git('status','--porcelain=v1','--untracked-files=all'):raise ValueError('Refusing dirty checkout')
    if (repo/'python/gmatpy/BUILD_PROVENANCE.json').exists():raise ValueError('Remove stale generated provenance from new checkout')
    index=Path(git('rev-parse','--git-path','index').decode().strip());index=index if index.is_absolute() else repo/index
    index_sha=sha(index);records=[]
    for raw in git('ls-files','--stage','-z').split(b'\0'):
        if not raw:continue
        metadata,name=raw.split(b'\t',1);mode,blob,stage=metadata.decode().split();name=os.fsdecode(name)
        if stage!='0':raise ValueError('Unmerged index')
        if mode=='160000':records.append({'path':name,'type':'gitlink','git_blob':blob,'git_mode':mode});continue
        path=repo/name;data=os.readlink(path).encode() if mode=='120000' else path.read_bytes()
        actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if actual!=blob:raise ValueError('Checkout bytes differ from Git blob: '+name)
        records.append({'path':name,'type':'symlink' if mode=='120000' else 'file','git_blob':blob,'git_mode':mode,'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)})
    output.mkdir(parents=True,exist_ok=False)
    manifest={'source_revision':revision,'git_tree_sha1':git('rev-parse','HEAD^{tree}').decode().strip(),'files':sorted(records,key=lambda r:r['path'])}
    working=output/'WORKING_TREE.json';working.write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    env['SOURCE_DATE_EPOCH']=git('show','-s','--format=%ct',revision).decode().strip()
    def build(source,dest):
        subprocess.run([sys.executable,'-m','build','--sdist','--no-isolation','--outdir',str(dest),str(source)],cwd=output,env=env,check=True)
        archives=list(dest.glob('*.tar.gz'))
        if len(archives)!=1:raise ValueError('Expected one source archive')
        return archives[0]
    seed=build(repo,output/'seed')
    sys.path.insert(0,str(repo/'python/tools'))
    from record_source import record,source_files
    from check_distribution import check
    by_path={r['path']:r for r in records}
    with tarfile.open(seed) as archive:
        for item in source_files(archive):
            source=by_path.get(item['path'])
            if source is None or source['type']!='file' or source['sha256']!=item['sha256'] or int(source['git_mode'],8)&0o777!=item['mode']:
                raise ValueError('Sdist input differs from committed file: '+item['path'])
        archive.extractall(output/'snapshot',filter='data')
    roots=list((output/'snapshot').iterdir())
    if len(roots)!=1:raise ValueError('Expected one snapshot root')
    provenance=roots[0]/'python/gmatpy/BUILD_PROVENANCE.json'
    provenance.write_text(json.dumps(record(seed,revision,sha(working)),sort_keys=True,indent=2)+'\n')
    final=build(roots[0],output/'artifacts');check(final,source_manifest=provenance)
    if git('status','--porcelain=v1','--untracked-files=all') or git('rev-parse','HEAD').decode().strip()!=revision or sha(index)!=index_sha:
        raise ValueError('Checkout/index changed during freeze')
    receipt={'source_revision':revision,'git_tree_sha1':manifest['git_tree_sha1'],'working_tree_manifest_sha256':sha(working),'source_tree_sha256':json.loads(provenance.read_text())['source_tree_sha256'],'source_archive_sha256':sha(final),'source_archive':final.name,'source_date_epoch':env['SOURCE_DATE_EPOCH']}
    (output/'SOURCE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--revision',required=True);a=p.parse_args();freeze(a.repo,a.output,a.revision)
