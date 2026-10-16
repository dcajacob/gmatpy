"""Generate fixed independent SciPy spline expectations on the qualified host."""
import itertools,json
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline
rng=np.random.default_rng(20261015);records=[]
for kind,descending,refill,case in itertools.product(range(2),range(2),range(2),range(40)):
 x=np.cumsum(rng.uniform(.1,2,5));y=rng.normal(0,2,5);q=np.linspace(x[0]-.1,x[-1]+.1,31)
 oracle=CubicSpline(x,y,bc_type='natural' if kind==0 else 'not-a-knot');expected=oracle(q)
 outside=(q<x[0])|(q>x[-1]);segment=3 if descending else 0
 expected[outside]=np.polyval(oracle.c[:,segment],q[outside]-x[segment])
 if descending:x,y=x[::-1],y[::-1]
 records.append({'kind':kind,'refill':refill,'x':x.tolist(),'y':y.tolist(),'q':q.tolist(),'expected':expected.tolist()})
p=Path(__file__).with_name('spline_oracle.json');p.write_text(json.dumps({'method':'Independent SciPy natural/not-a-knot, retained GMAT extrapolation convention','cases':records})+'\n');print('Recorded',len(records),'cases /',sum(len(r['q']) for r in records),'values')
