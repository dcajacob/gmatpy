"""Native comparisons with saved SciPy values and focused analytic regressions.

The fixed values were generated with generate_spline_oracle.py (seed 20261015).
They are not regenerated on CI. This checks mathematical regression cases, not
all possible inputs or every inherited numerical routine.
The additional endpoint/scale/refill cases below have independent exact-knot,
linear and rational natural-spline expectations; no SciPy runs on CI.
"""
import ctypes as C,hashlib,json,math,platform,shutil,subprocess,sys
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

# New regressions are deliberately separate from the frozen SciPy oracle.
# For five equally spaced knots x_i=i*h and y_i=i^2, the natural boundary
# conditions give second derivatives [0,18/7,12/7,18/7,0]/h^2. Substitution at
# the four half-knots gives these rational values independently of either
# implementation. Decimal h=1e-110 is only approximately uniform in binary64;
# the scaled tolerance permits its rounding while still rejecting Inf/NaN.
half_values=[19/56,125/56,349/56,691/56]
from fractions import Fraction
def last_unit_interval_reference(values,query):
 # Exact rational solution of the natural unit-grid continuity equations:
 # 4*M1+M2=R1, M1+4*M2+M3=R2, M2+4*M3=R3. Only the final
 # interval's M3 is needed here; M4=0. Float inputs retain their exact bits.
 y=[Fraction.from_float(value) for value in values]
 rhs=[6*(y[i+2]-2*y[i+1]+y[i]) for i in range(3)]
 middle=(4*rhs[1]-rhs[0]-rhs[2])/14
 left_second=(rhs[2]-middle)/4
 a=4-Fraction.from_float(query);b=1-a
 return float(a*y[3]+b*y[4]+(a**3-a)*left_second/6)
regressions=[]
def verify_case(name,x_values,y_values,queries,expected,*,refill=0,exact=False,relative=False):
 x=(C.c_double*5)(*x_values);y=(C.c_double*5)(*y_values)
 q=(C.c_double*len(queries))(*queries);out=(C.c_double*len(queries))()
 status=h.evaluate_spline(0,x,y,q,len(q),out,refill)
 finite=all(math.isfinite(value) for value in out)
 error=max((abs(a-b)/((abs(b) or 1.) if relative else 1+abs(b)) for a,b in zip(out,expected)),default=0.) if finite else math.inf
 passed=status==0 and finite and (list(out)==list(expected) if exact else error<2e-12)
 record={'name':name,'x':x_values,'y':y_values,'queries':queries,'expected':expected,
         'actual':[value if math.isfinite(value) else str(value) for value in out],
         'status':status,'finite':finite,'exact':exact,'relative_error':relative,'refill_mode':refill,
         'maximum_scaled_error':error if math.isfinite(error) else str(error),'passed':passed}
 regressions.append(record)
 if not passed:raise ValueError('Spline regression failed: '+json.dumps(record))
for descending in (False,True):
 label='descending' if descending else 'ascending'
 knots=[0.,1.,2.,3.,4.];values=[1e12,2e12,3e12,4e12,1e-12]
 if descending:knots,values=knots[::-1],values[::-1]
 verify_case('exact_dynamic_range_knots_'+label,knots,values,knots,values,exact=True)
 near=[math.nextafter(4.,0.),4.-1e-12]
 reference_values=[1e12,2e12,3e12,4e12,1e-12]
 verify_case('near_dynamic_range_endpoint_'+label,knots,values,near,
             [last_unit_interval_reference(reference_values,query) for query in near])
 # The binary64 solve gives zero curvature for this almost-linear dataset.
 # The exact rational natural-spline reference still retains the small final
 # value and catches cancellation from anchoring every interval at its left.
 linear_endpoint=[4e12,3e12,2e12,1e12,1e-8]
 verify_case('near_small_linear_endpoint_'+label,
             [0.,1.,2.,3.,4.][::-1] if descending else [0.,1.,2.,3.,4.],
             linear_endpoint[::-1] if descending else linear_endpoint,near,
             [last_unit_interval_reference(linear_endpoint,query) for query in near])
 large_knots=[i*1e100 for i in range(5)];small_values=[i*1e-250 for i in range(5)]
 if descending:large_knots,small_values=large_knots[::-1],small_values[::-1]
 # The physical slope underflows, although normalized interpolation remains
 # finite. Relative error is essential: a unit-sized denominator would accept
 # an erroneous zero for every value in this case.
 verify_case('linear_small_amplitude_large_spacing_'+label,large_knots,small_values,
             [i*1e100 for i in (.5,1.5,3.5)],[i*1e-250 for i in (.5,1.5,3.5)],relative=True)
 for spacing,name in ((1.,'unit'),(1e-110,'tiny')):
  knots=[i*spacing for i in range(5)];values=[float(i*i) for i in range(5)]
  if descending:knots,values=knots[::-1],values[::-1]
  verify_case('natural_half_knots_'+name+'_'+label,knots,values,
              [(i+.5)*spacing for i in range(4)],half_values)
 knots=[0.,1.,2.,3.,4.];values=[float(i*i) for i in range(5)]
 if descending:knots,values=knots[::-1],values[::-1]
 verify_case('shape_changing_clear_refill_'+label,knots,values,
             [.5,1.5,2.5,3.5],half_values,refill=2)
# Preserve finite extrapolation of flat/linear data. Unnormalized t*u or an
# overflowing normalized coordinate must not create 0*Inf on these segments.
verify_case('distant_constant',[0.,1.,2.,3.,4.],[1.]*5,[-1e200,1e200],[1.,1.],exact=True)
verify_case('distant_linear',[0.,1.,2.,3.,4.],[0.,1.,2.,3.,4.],[-1e200,1e200],[-1e200,1e200],exact=True)
verify_case('distant_linear_tiny_spacing',[i*1e-110 for i in range(5)],
            [i*1e-110 for i in range(5)],[-1e200,1e200],[-1e200,1e200],exact=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'cases':len(cases),'compared_values':sum(len(r['q']) for r in cases),'maximum_scaled_error':maximum,'tolerance':1e-10,'installed_module':str(gmatpy.__file__),'library_sha256':sha(library),'oracle_sha256':sha(base/'spline_oracle.json'),'harness_sha256':sha(harness),'compile_command':command,'analytic_regressions':{'cases':len(regressions),'compared_values':sum(len(r['queries']) for r in regressions),'scaled_tolerance':2e-12,'results':regressions},'note':'Fresh executed comparisons with pre-recorded independent SciPy expectations, which are not regenerated, plus separate exact-knot/linear/rational natural-spline regressions.'}
(output/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
