"""New native comparisons with previously recorded independent SciPy values.

The fixed values were generated with generate_spline_oracle.py (seed 20261015).
They are not regenerated on CI. This checks mathematical regression cases, not
all possible inputs or every inherited numerical routine.
"""
import ctypes as C,hashlib,json,platform,shutil,subprocess,sys
from pathlib import Path
import gmatpy
base=Path(__file__).resolve().parent;source=Path(sys.argv[1]);output=Path(sys.argv[2]);output.mkdir(exist_ok=False)
native=Path(gmatpy.__file__).resolve().parent/'_native';mac=platform.system()=='Darwin'
libraries=list(native.glob('libGmatUtil.dylib' if mac else 'libGmatUtil.so.*'));assert len(libraries)==1
library=libraries[0];harness=output/('harness.dylib' if mac else 'harness.so');includes=source/'src/gmatutil'
compiler=shutil.which('clang++' if mac else 'g++');assert compiler
command=[compiler,'-dynamiclib' if mac else '-shared','-fPIC','-std=c++17','-O2']
if mac:command+=['-arch',platform.machine(),'-mmacosx-version-min=11.0']
command += [*[f'-I{includes/p}' for p in ['include','util','util/interpolator']],str(base/'spline_harness.cpp'),str(library),'-Wl,-rpath,'+str(native),'-o',str(harness)]
subprocess.run(command,check=True)
h=C.CDLL(str(harness));ptr=C.POINTER(C.c_double);h.evaluate_spline.argtypes=[C.c_int,ptr,ptr,ptr,C.c_int,ptr,C.c_int]
cases=json.loads((base/'spline_oracle.json').read_text())['cases'];maximum=0.
for n,r in enumerate(cases):
 x=(C.c_double*len(r['x']))(*r['x']);y=(C.c_double*len(r['y']))(*r['y']);q=(C.c_double*len(r['q']))(*r['q']);out=(C.c_double*len(q))()
 assert h.evaluate_spline(r['kind'],x,y,q,len(q),out,r['refill'])==0,n
 error=max(abs(a-b)/(1+abs(b)) for a,b in zip(out,r['expected']));maximum=max(maximum,error);assert error<1e-10,(n,error)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'cases':len(cases),'compared_values':sum(len(r['q']) for r in cases),'maximum_scaled_error':maximum,'tolerance':1e-10,'installed_module':str(gmatpy.__file__),'library_sha256':sha(library),'oracle_sha256':sha(base/'spline_oracle.json'),'harness_sha256':sha(harness),'compile_command':command,'note':'Fresh executed comparisons with pre-recorded independent SciPy expectations; expectations not regenerated in this run.'}
(output/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
