"""Build a target-native N0067 archive; never use the package's prebuilt library.

Linux aarch64 uses NAIF's Linux64 LP64 configuration with the x86-only -m64
removed. Native execution/type/object checks are mandatory; this is not a claim
that NAIF distributes an official Linux ARM64 package. Source terms stay intact.
"""
import argparse,concurrent.futures,hashlib,json,os,platform,shutil,subprocess,tarfile,urllib.request
from pathlib import Path,PurePosixPath


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(args,**kw):return subprocess.run(list(map(str,args)),check=True,**kw)


def build(target,root,archive=None,jobs=2,deployment='11.0'):
    system,arch=target.split('-',1)
    machine={'aarch64':'arm64','AMD64':'x86_64'}.get(platform.machine(),platform.machine())
    assert machine==arch,(machine,target)
    assert platform.system()==('Darwin' if system=='macos' else 'Linux')
    config=json.loads(Path(__file__).with_name('cspice-sources.json').read_text())['linux' if system=='linux' else target]
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=False)
    if archive is None:
        archive=root/'official.tar.Z'
        with urllib.request.urlopen(config['url'],timeout=60) as response,archive.open('wb') as out:shutil.copyfileobj(response,out)
    archive=Path(archive).resolve();assert sha(archive)==config['sha256'],'Unexpected NAIF archive bytes'
    expanded=root/'official.tar'
    with expanded.open('wb') as stream:run(['gzip','-dc',archive],stdout=stream)
    include=root/'include';src=root/'native-source';obj=root/'objects';lib=root/'lib'
    for directory in (include,src,obj,lib):directory.mkdir()
    source_records=[]
    with tarfile.open(expanded) as tar:
        for member in tar.getmembers():
            name=PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts:raise ValueError(member.name)
            public=member.name.startswith('cspice/include/') and name.suffix=='.h'
            native=member.name.startswith('cspice/src/cspice/') and name.suffix in ('.c','.h')
            if not(public or native):continue
            assert member.isfile()
            dest=(include if public else src)/name.name
            assert not dest.exists(),dest
            dest.write_bytes(tar.extractfile(member).read())
            source_records.append({'path':member.name,'sha256':sha(dest)})
    cc=shutil.which(os.environ.get('CC','clang' if system=='macos' else 'gcc'));assert cc
    flags=['-c','-ansi','-O2','-fPIC','-DNON_UNIX_STDIO','-fno-strict-aliasing']
    link_flags=[]
    if system=='macos':
        link_flags=['-arch',arch,'-mmacosx-version-min='+deployment]
        flags+=link_flags+['-Wno-shift-op-parentheses','-Wno-logical-op-parentheses','-Wno-parentheses']
    files=sorted(src.glob('*.c'));assert len(files)==2229,len(files)
    def compile_one(path):
        output=obj/(path.stem+'.o');args=[cc,*flags,'-I'+str(include),path,'-o',output]
        result=subprocess.run(list(map(str,args)),capture_output=True,text=True)
        if result.returncode:raise RuntimeError(str(path)+'\n'+result.stdout+result.stderr)
        return output
    objects=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        for n,output in enumerate(pool.map(compile_one,files),1):
            objects.append(output)
            if n%200==0:print('CSPICE native compile',n,'/',len(files),flush=True)
    library=lib/'cspice.a';ar=shutil.which('ar');assert ar
    for offset in range(0,len(objects),100):run([ar,'rcs',library,*objects[offset:offset+100]],stdout=subprocess.DEVNULL)
    run(['ranlib',library])
    members=subprocess.check_output([ar,'t',str(library)],text=True).splitlines()
    # Apple's ar lists its ranlib symbol-table member; it is not an object.
    symbol_tables={'__.SYMDEF','__.SYMDEF SORTED','__.SYMDEF_64','__.SYMDEF_64 SORTED'}
    object_members=[name for name in members if name not in symbol_tables]
    assert len(object_members)==len(files) and set(object_members)=={p.name for p in objects}
    probe=root/'abi-probe.c';probe.write_text(r'''#include "SpiceUsr.h"
#include "f2c.h"
#include <stdio.h>
#include <float.h>
int main(void) {
 unsigned int one=1;
 if(sizeof(SpiceInt)!=4 || sizeof(integer)!=4 || sizeof(long)!=8 || sizeof(double)!=8 || DBL_MANT_DIG!=53 || DBL_MAX_EXP!=1024 || *(unsigned char*)&one!=1) return 2;
 printf("{\"SpiceInt\":%d,\"f2c_integer\":%d,\"long\":%d,\"double\":%d,\"little_endian\":true,\"toolkit\":\"%s\"}\n",(int)sizeof(SpiceInt),(int)sizeof(integer),(int)sizeof(long),(int)sizeof(double),tkvrsn_c("TOOLKIT")); return 0;
}
''')
    # The probe's JSON escaping is ordinary C string syntax, not a shell command.
    exe=root/'abi-probe';run([cc,*link_flags,'-I'+str(include),probe,library,'-lm','-o',exe])
    abi=json.loads(subprocess.check_output([str(exe)],text=True));assert abi['toolkit']=='CSPICE_N0067',abi
    machine_evidence=subprocess.check_output(['file',str(objects[0])],text=True)
    if system=='macos':assert subprocess.check_output(['lipo','-archs',str(exe)],text=True).strip()==arch
    else:
        headers=subprocess.check_output(['readelf','-h',str(objects[0])],text=True)
        assert ('AArch64' if arch=='arm64' else 'Advanced Micro Devices X86-64') in headers
    record={'target':target,'native_machine':platform.machine(),'archive':config,'native_sources':source_records,'compiler':subprocess.check_output([cc,'--version'],text=True).splitlines()[0],'compile_flags':flags,'library_sha256':sha(library),'header_sha256':{p.name:sha(p) for p in sorted(include.glob('*.h'))},'abi':abi,'object_architecture':machine_evidence.strip(),'linux_arm64_port':system=='linux' and arch=='arm64','note':'All 2229 C files rebuilt natively. No precompiled NAIF library copied. Native type/endianness/execution checks required. Owner product release determination remains separate.'}
    (root/'BUILD_DEPENDENCY.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    expanded.unlink()
    print('CSPICE_NATIVE_OK',target,record['library_sha256'],abi,flush=True)
    return root

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',required=True,choices=['linux-x86_64','linux-arm64','macos-x86_64','macos-arm64']);p.add_argument('--output',type=Path,required=True);p.add_argument('--archive',type=Path);p.add_argument('--jobs',type=int,default=2,choices=[1,2]);p.add_argument('--deployment-target',default='11.0');a=p.parse_args();build(a.target,a.output,a.archive,a.jobs,a.deployment_target)
