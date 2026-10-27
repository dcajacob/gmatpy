"""Fresh native Windows index install and numerical checks of exact 0.2.1 files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile

import windows_release_021 as guard


def run(command,cwd,env,log):
    with log.open('w') as output:
        completed=subprocess.run(list(map(str,command)),cwd=cwd,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=600)
    if completed.returncode:print(log.read_text(errors='replace')[-18000:])
    completed.check_returncode()


def verify(output):
    m=guard.load_config();guard.require(os.name=='nt' and platform.machine().upper()=='AMD64','Native Windows x64 required')
    record=next(r for r in m['files'] if r['python']==platform.python_version())
    guard.check_public_state(m,guard.public_snapshot(),complete=True)
    output=output.resolve();output.mkdir(exist_ok=False)
    source=guard.download_artifact(m,m['source_artifact'],output/'source-artifact')
    guard.require(json.loads((source/'SOURCE_RECEIPT.json').read_text())==m['source_receipt'],'Wrong test source')
    with tarfile.open(source/'artifacts/gmatpy-0.2.1.tar.gz') as t:t.extractall(output/'source',filter='data')
    ci=output/'source/gmatpy-0.2.1/python/ci';tests=ci.parent/'tests'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PIP_NO_CACHE_DIR='1',PYTHONUTF8='1',CMAKE_GENERATOR='Ninja')
    env.pop('PYTHONPATH',None)
    venv=output/'venv';run([sys.executable,'-m','venv',venv],output,env,output/'venv.log')
    py=venv/'Scripts/python.exe';outside=output/'outside';outside.mkdir()
    # Resolve and install through the normal public index, with no artifact path.
    run([py,'-m','pip','install','--index-url','https://pypi.org/simple','--only-binary=:all:',
         '--report',output/'index-install.json','gmatpy==0.2.1','pytest==9.1.1'],outside,env,output/'index-install.log')
    receipt=json.loads((output/'index-install.json').read_text())
    package=next(r for r in receipt['install'] if r['metadata']['name']=='gmatpy')
    guard.require(package['download_info']['archive_info']['hashes']['sha256']==record['sha256'],'Index installed different native wheel')
    url=package['download_info']['url'];guard.require(url.startswith('https://files.pythonhosted.org/') and url.endswith('/'+record['wheel']),'Unexpected public index URL')
    run([py,'-m','pip','download','--index-url','https://pypi.org/simple','--only-binary=:all:',
         '--no-deps','--dest',output/'download','gmatpy==0.2.1'],outside,env,output/'download.log')
    wheel=output/'download'/record['wheel'];guard.require(guard.sha(wheel)==record['sha256'] and wheel.stat().st_size==record['bytes'],'Downloaded public file differs')
    clean=dict(env);win=Path(os.environ['SystemRoot']);clean['PATH']=os.pathsep.join(map(str,[py.parent,win/'System32',win]))
    code='''import importlib.util,pathlib,sys,hashlib,zipfile
import gmatpy
root=pathlib.Path(gmatpy.__file__).resolve().parent.parent
assert root.is_relative_to(pathlib.Path(sys.prefix).resolve())
assert gmatpy.__version__=='0.2.1'
with zipfile.ZipFile(sys.argv[1]) as z:
 for n in z.namelist():
  if n.startswith('gmatpy/') and not n.endswith('/'):
   assert hashlib.sha256((root/n).read_bytes()).digest()==hashlib.sha256(z.read(n)).digest(),n
print('PUBLIC_INDEX_INSTALLED_BYTES_AND_IMPORT_OK',root)
'''
    run([py,'-I','-c',code,wheel],outside,clean,output/'installed-bytes.log')
    run([py,'-m','pytest','-q','-ra','--import-mode=prepend',tests],outside,env,output/'pytest.log')
    run([py,ci/'sample_states.py',output/'states.json'],outside,clean,output/'sample.log')
    run([py,ci/'check_states.py',output/'states.json'],outside,clean,output/'state-comparison.json')
    result={'result':'passed','version':'0.2.1','python':platform.python_version(),'wheel':record['wheel'],
            'sha256':record['sha256'],'public_url':url,'installed_bytes_and_import':'passed',
            'tests':(output/'pytest.log').read_text().splitlines()[-1],
            'state_comparison':json.loads((output/'state-comparison.json').read_text()),'source_revision':m['qualification_source']}
    guard.require(__import__('re').fullmatch(r'203 passed, 6 skipped, 3 subtests passed in [0-9.]+s',result['tests']),'Incomplete public installed test outcome')
    evidence=output/'evidence';evidence.mkdir()
    for name in ('index-install.json','index-install.log','installed-bytes.log','pytest.log','states.json','state-comparison.json'):
        shutil.copyfile(output/name,evidence/name)
    (evidence/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    print('WINDOWS_PUBLIC_INDEX_OK',json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    verify(parser.parse_args().output)
