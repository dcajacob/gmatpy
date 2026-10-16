"""Build/repair and test the full headless wheel from one immutable sdist.

Run using an isolated standard-ABI CPython 3.14 tools venv with requirements.txt
installed. Exact patch versions are recorded; the pinned native images may differ.
No publishing, remote upload or cache; all outputs go to a new --output directory.
"""
import argparse,hashlib,json,os,platform,shutil,subprocess,sys,sysconfig,tarfile,zipfile
from pathlib import Path


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(command, *, cwd, env, log, timeout=5400):
    command=list(map(str,command));print('+',*command,flush=True)
    with log.open('w') as stream:
        result=subprocess.run(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
    if result.returncode:
        print(log.read_text(errors='replace')[-10000:],flush=True)
        raise RuntimeError(f'{command[0]} exited {result.returncode}: {log}')


def qualify(args):
    if 'GMAT_PY_PROFILE' in os.environ and os.environ['GMAT_PY_PROFILE'] != 'extended':
        raise ValueError('GMAT_PY_PROFILE is obsolete; qualification builds one full headless package (SPICE included)')
    assert sys.version_info[:2]==(3,14) and not sysconfig.get_config_var('Py_GIL_DISABLED'),sys.version
    target=args.target;system,arch=target.split('-');actual=platform.machine().lower()
    assert actual==({'arm64':'aarch64','x86_64':'x86_64'}[arch] if system=='linux' else arch),(target,actual)
    assert platform.system()==('Linux' if system=='linux' else 'Darwin')
    source_archive=args.sdist.resolve();output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',SOURCE_DATE_EPOCH='1790812800',CMAKE_BUILD_PARALLEL_LEVEL='2',CMAKE_GENERATOR='Unix Makefiles')
    environment['PATH']=str(Path(sys.executable).parent)+os.pathsep+environment['PATH']
    environment.pop('PYTHONPATH',None);environment.pop('LD_LIBRARY_PATH',None);environment.pop('DYLD_LIBRARY_PATH',None)
    environment.pop('GMAT_PY_PROFILE',None)
    if system=='macos':environment.update(MACOSX_DEPLOYMENT_TARGET='11.0',ARCHFLAGS=f'-arch {arch}')
    source_root=output/'source';source_root.mkdir()
    with tarfile.open(source_archive) as archive:archive.extractall(source_root,filter='data')
    sources=list(source_root.iterdir());assert len(sources)==1;source=sources[0];ci=source/'python/ci';tools=source/'python/tools'
    manifest=source/'python/gmatpy/BUILD_PROVENANCE.json'
    run([sys.executable,tools/'check_distribution.py',source_archive,'--source-manifest',manifest],cwd=output,env=environment,log=output/'sdist-check.log')
    spice=args.cspice.resolve() if args.cspice else output/'cspice'
    if not args.cspice:
        command=[sys.executable,ci/'build_cspice.py','--target',target,'--output',spice,'--jobs','2']
        if args.archive:command+=['--archive',args.archive.resolve()]
        run(command,cwd=output,env=environment,log=output/'cspice-build.log')
    dependency=json.loads((spice/'BUILD_DEPENDENCY.json').read_text());assert dependency['target']==target
    assert digest(spice/'lib/cspice.a')==dependency['library_sha256']
    shutil.copy2(spice/'BUILD_DEPENDENCY.json',output/'CSPICE_BUILD_DEPENDENCY.json')
    results={'target':target,'python':sys.version,'platform':platform.platform(),'sdist_sha256':digest(source_archive),'source_tree_sha256':json.loads(manifest.read_text())['source_tree_sha256'],'cspice_library_sha256':dependency['library_sha256'],'profiles':{}}
    run([sys.executable,'-m','pip','freeze'],cwd=output,env=environment,log=output/'python-tools.txt')
    # Retain the historical evidence key; only one standard artifact is built.
    profile='extended'
    dest=output/profile;dest.mkdir();raw=dest/'raw';repaired=dest/'wheelhouse';repaired.mkdir()
    command=[sys.executable,'-m','build','--wheel','--no-isolation','--outdir',raw,source,'-Cbuild-dir='+str(dest/'native'),'-Ccmake.define.CSPICE_DIR='+str(spice)]
    if system=='macos':command+=['-Ccmake.define.GMAT_PY_EXPERIMENTAL_MACOS=ON','-Ccmake.define.CMAKE_OSX_ARCHITECTURES='+arch,'-Ccmake.define.CMAKE_OSX_DEPLOYMENT_TARGET=11.0']
    run(command,cwd=output,env=environment,log=dest/'build.log')
    wheels=list(raw.glob('*.whl'));assert len(wheels)==1
    if system=='linux':
        manylinux='manylinux_2_28_'+('aarch64' if arch=='arm64' else arch)
        run([sys.executable,'-m','auditwheel','show',wheels[0]],cwd=output,env=environment,log=dest/'auditwheel-before.log')
        run([sys.executable,'-m','auditwheel','repair','--plat',manylinux,wheels[0],'-w',repaired],cwd=output,env=environment,log=dest/'repair.log')
    else:
        run([Path(sys.executable).parent/'delocate-wheel','--require-archs',arch,'-w',repaired,wheels[0]],cwd=output,env=environment,log=dest/'repair.log')
    wheels=list(repaired.glob('*.whl'));assert len(wheels)==1;wheel=wheels[0]
    checker='check_wheel.py' if system=='linux' else 'check_macos_wheel.py'
    command=[sys.executable,tools/checker,wheel,'--source-manifest',manifest]
    if system=='macos':command+=['--arch',arch]
    run(command,cwd=output,env=environment,log=dest/'binary-contents-check.log')
    if system=='linux':
        assert manylinux in wheel.name,wheel.name
        run([sys.executable,'-m','auditwheel','show',wheel],cwd=output,env=environment,log=dest/'auditwheel-after.log')
    release=subprocess.run([sys.executable,str(tools/'check_distribution.py'),str(wheel),'--release','--source-manifest',str(manifest)],cwd=output,env=environment,capture_output=True,text=True)
    (dest/'release-hold.log').write_text(release.stdout+release.stderr)
    if release.returncode:
        unresolved=release.stderr.splitlines()
        assert release.returncode==1 and unresolved and unresolved[0]=='Release review unresolved:',release
        assert len(unresolved)==2 and unresolved[1].strip().startswith('cspice-derived-export-designation:'),release
        results['release_hold']='owner_decision_required'
    else:
        results['release_hold']=None
    test_env=dest/'test-env';run([sys.executable,'-m','venv','--without-pip',test_env],cwd=output,env=environment,log=dest/'venv.log');test_python=test_env/'bin/python'
    # pip's --python installs into the empty test venv. No source/editable install.
    command=[sys.executable,'-m','pip','--python',test_python,'install',wheel,'pytest==9.1.1','iniconfig==2.3.1','packaging==26.0','pluggy==1.6.0','pygments==2.19.2']
    if args.wheelhouse:command+=['--no-index','--find-links',args.wheelhouse.resolve()]
    run(command,cwd=output,env=environment,log=dest/'install.log')
    outside=dest/'outside-source';outside.mkdir()
    # Verify every installed package byte, including native libraries, against this wheel.
    code='''import hashlib,importlib.util,pathlib,zipfile,sys
root=pathlib.Path(importlib.util.find_spec('gmatpy').origin).parent.parent
assert not str(root).startswith(sys.argv[2])
with zipfile.ZipFile(sys.argv[1]) as z:
 for n in z.namelist():
  if n.startswith('gmatpy/') and not n.endswith('/'):
   assert hashlib.sha256((root/n).read_bytes()).digest()==hashlib.sha256(z.read(n)).digest(),n
print('INSTALLED_BYTES_OK',root)
'''
    run([test_python,'-c',code,wheel,source],cwd=outside,env=environment,log=dest/'installed-bytes.log')
    run([test_python,'-m','pytest','-q','-ra','--import-mode=prepend',source/'python/tests'],cwd=outside,env=environment,log=dest/'pytest.log',timeout=600)
    run([test_python,ci/'sample_states.py',dest/'states.json'],cwd=outside,env=environment,log=dest/'sample.log',timeout=180)
    run([test_python,ci/'check_states.py',dest/'states.json'],cwd=outside,env=environment,log=dest/'state-comparison.json')
    run([test_python,ci/'verify_splines.py',source,dest/'spline'],cwd=outside,env=environment,log=dest/'spline.log',timeout=180)
    run([test_python,ci/'verify_msise.py',source,dest/'msise'],cwd=outside,env=environment,log=dest/'msise.log',timeout=180)
    results['profiles'][profile]={'wheel':wheel.name,'sha256':digest(wheel),'bytes':wheel.stat().st_size,'tests':(dest/'pytest.log').read_text().splitlines()[-1],'state_comparison':json.loads((dest/'state-comparison.json').read_text()),'spline_comparison':json.loads((dest/'spline/RESULTS.json').read_text()),'msise_comparison':json.loads((dest/'msise/RESULTS.json').read_text())}
    (output/'RESULTS.json').write_text(json.dumps(results,indent=2)+'\n')
    print('PROFILE_QUALIFIED',profile,json.dumps(results['profiles'][profile]),flush=True)
    hashes={str(p.relative_to(output)):digest(p) for p in output.rglob('*') if p.is_file() and (p.suffix in ('.log','.json','.txt','.whl')) and not any(part in ('source','native','test-env','raw','cspice') for part in p.relative_to(output).parts)}
    (output/'EVIDENCE_SHA256.json').write_text(json.dumps(hashes,indent=2,sort_keys=True)+'\n')
    print('QUALIFIED',json.dumps(results),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',required=True,choices=['linux-x86_64','linux-arm64','macos-x86_64','macos-arm64']);p.add_argument('--sdist',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--cspice',type=Path);p.add_argument('--archive',type=Path);p.add_argument('--wheelhouse',type=Path);qualify(p.parse_args())
