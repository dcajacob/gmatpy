"""Compare with fresh NASA-source engine/common-NASA-input samples.

NASA9363e129 science sources plus explicitly recorded Python/build/startup
adapters, Linux x86_64 CPython3.14.7 extended. Exact source/input/native hashes
and claim limits are embedded in reference-states.json. This is not an official
unmodified NASA build or independent empirical truth. Position km, velocity km/s.
"""
import json, math, sys
from pathlib import Path
reference=json.loads(Path(__file__).with_name('reference-states.json').read_text())['records']
actual=json.loads(Path(sys.argv[1]).read_text())['records']
assert actual.keys()==reference.keys()
errors=[0.,0.]
for name, expected in reference.items():
    rows=actual[name]
    if isinstance(expected[0],(int,float)):expected=[expected];rows=[rows]
    assert len(rows)==len(expected),(name,len(rows))
    for a,b in zip(rows,expected):
        assert len(a)==len(b)==6
        for i,(x,y) in enumerate(zip(a,b)):
            error=abs(x-y);group=i//3;errors[group]=max(errors[group],error)
            assert math.isfinite(x) and error<=[2e-7,2e-10][group],(name,i,x,y,error)
print(json.dumps({'position_tolerance_km':2e-7,'velocity_tolerance_km_s':2e-10,'maximum_position_error_km':errors[0],'maximum_velocity_error_km_s':errors[1]}))
