"""Sample identical propagation/frame inputs in independent profile processes."""
import json
import sys
from pathlib import Path
import gmatpy as g
state=[7000,120,-80,-.2,7.4,1]
epoch='2024-01-01T00:00:00Z'
records={}
for name,forces in [('default',g.ForceModel()),('drag70',g.ForceModel(degree=70,order=70,drag=True)),
                    ('jgm3',g.ForceModel(gravity_model='JGM3',degree=70)),
                    ('point',g.ForceModel(degree=0,sun=False,moon=False,srp=False))]:
 records[name]=[sample.state for sample in g.propagate(state,epoch,[0,60,60,600],forces=forces)]
records['icrf']=g.transform_state(state,epoch,to_frame='EarthICRF')
records['fixed']=g.transform_state(state,epoch,to_frame='EarthFixed')
payload=json.dumps({'profile':g.capabilities().profile,'records':records})
if len(sys.argv)>1:
 Path(sys.argv[1]).write_text(payload+'\n')
else:
 print(payload)
