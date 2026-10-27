"""Negative tests for the Windows extension's irreversible publication boundary."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).parent))
import windows_release_021 as guard


def snapshot(m):
    return {v:{'urls':[{'filename':n,'size':f['bytes'],'digests':{'sha256':f['sha256']},'yanked':False}
                      for n,f in records.items()]} for v,records in m['preserve'].items()}


def test_fixed_config_and_preserved_release_only():
    m=guard.load_config();assert guard.check_public_state(m,snapshot(m))==set()
    with pytest.raises(ValueError):guard.check_public_state(m,snapshot(m),complete=True)


def test_identical_partial_resume_and_complete_release():
    m=guard.load_config();p=snapshot(m)
    for i,f in enumerate(m['files'],1):
        p['0.2.1']['urls'].append({'filename':f['wheel'],'size':f['bytes'],'digests':{'sha256':f['sha256']}})
        assert len(guard.check_public_state(m,p))==i
    assert len(guard.check_public_state(m,p,complete=True))==4


@pytest.mark.parametrize('mutation',['old020hash','old021hash','old021size','old021missing','unknown','newhash','newsize','yanked','duplicate'])
def test_never_replace_or_ignore_conflicting_public_files(mutation):
    m=guard.load_config();p=snapshot(m);f=m['files'][0]
    item={'filename':f['wheel'],'size':f['bytes'],'digests':{'sha256':f['sha256']}}
    p['0.2.1']['urls'].append(item)
    if mutation=='old020hash':p['0.2.0']['urls'][0]['digests']['sha256']='0'*64
    if mutation=='old021hash':p['0.2.1']['urls'][0]['digests']['sha256']='0'*64
    if mutation=='old021size':p['0.2.1']['urls'][0]['size']+=1
    if mutation=='old021missing':p['0.2.1']['urls'].pop(0)
    if mutation=='unknown':item['filename']='unknown.whl'
    if mutation=='newhash':item['digests']['sha256']='0'*64
    if mutation=='newsize':item['size']+=1
    if mutation=='yanked':item['yanked']=True
    if mutation=='duplicate':p['0.2.1']['urls'].append(copy.deepcopy(item))
    with pytest.raises(ValueError):guard.check_public_state(m,p)


@pytest.mark.parametrize('key',['GITHUB_REPOSITORY','GITHUB_REF','GITHUB_EVENT_NAME','GITHUB_RUN_ATTEMPT','GITHUB_WORKFLOW_REF'])
def test_required_existing_publisher_context(key):
    env={'GITHUB_REPOSITORY':guard.REPOSITORY,'GITHUB_REF':'refs/heads/main','GITHUB_EVENT_NAME':'workflow_dispatch',
         'GITHUB_RUN_ATTEMPT':'1','GITHUB_WORKFLOW_REF':guard.REPOSITORY+'/.github/workflows/publish-pypi.yml@refs/heads/main'}
    guard.context(env);env[key]='wrong'
    with pytest.raises(ValueError):guard.context(env)


def test_preserves_pypi_review_gate_and_oidc_identity():
    workflow=(guard.ROOT/'.github/workflows/publish-pypi.yml').read_text().split('  publish021windows:',1)[1]
    assert 'name: pypi' in workflow and "github.ref == 'refs/heads/main'" in workflow
    assert 'packages-dir: publish-windows/' in workflow and 'skip-existing: \'false\'' in workflow
    assert 'contents: read' in workflow and 'actions: read' in workflow and 'id-token: write' in workflow
    assert 'contents: write' not in workflow and 'secrets.' not in workflow


def test_legacy_public_verifier_accepts_only_known_windows_additions():
    import download_release_021 as legacy
    import release_021
    m=guard.load_config();p=snapshot(m)
    for f in m['files']:
        p['0.2.1']['urls'].append({'filename':f['wheel'],'size':f['bytes'],'digests':{'sha256':f['sha256']}})
    public={'info':{'version':'0.2.1'},'releases':{v:d['urls'] for v,d in p.items()}}
    old=json.loads(release_021.CONFIG.read_text())
    assert len(legacy.check_listing(old,public))==21
    public['releases']['0.2.1'][-1]['digests']['sha256']='0'*64
    with pytest.raises(ValueError):legacy.check_listing(old,public)
