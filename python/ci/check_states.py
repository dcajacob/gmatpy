"""Compare DE405 propagation/frame results with the qualified Linux reference.

Reference: source tree 4e4c39e637a4da4f521be024359f84438462f5ab4b3dd16e11b725329b656167,
Linux x86_64 CPython 3.14, extended profile. This is a regression comparison,
not independent validation of the ephemeris. Position km, velocity km/s.
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
