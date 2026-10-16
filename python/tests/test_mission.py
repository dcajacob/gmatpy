"""Numerical and lifetime checks for the first core mission increment."""
import math
from pathlib import Path

import pytest
import gmatpy as g

EPOCH = "2020-07-20T12:00:00Z"
MU = 398600.4415
STATE = (7000., 0., 0., 0., math.sqrt(MU/7000), 0.)
POINT = g.ForceModel(degree=0, sun=False, moon=False, srp=False)
extended = pytest.mark.skipif(g.capabilities().profile != "extended", reason="extended-profile workflow")


@extended
def test_two_spacecraft_share_native_propagator_and_match_independent_orbits():
    other = (8000., 0., 0., 0., math.sqrt(MU/8000), 0.)
    times = [0, 600, 600, 1800]
    actual = g.propagate_many({"first": STATE, "second": other}, EPOCH, times, forces=POINT)
    for name, state in (("first", STATE), ("second", other)):
        expected = g.propagate(state, EPOCH, times, forces=POINT)
        for one, two in zip(actual[name], expected):
            assert one.state == pytest.approx(two.state, rel=0, abs=2e-8)
        assert actual[name][1] == actual[name][2]
    assert math.dist(actual["first"][-1].position_km, actual["second"][-1].position_km) > 1000


@extended
@pytest.mark.parametrize("burn_time", [0., 60., 120.])
def test_native_impulse_has_exact_jump_and_correct_following_arc(burn_time):
    dv = (.001, .01, -.002)
    offsets = sorted([0., burn_time, burn_time, burn_time+120])
    prior = g.propagate(STATE, EPOCH, [burn_time], forces=POINT)[0]
    actual = g.propagate_mission(STATE, EPOCH, offsets, forces=POINT,
                                 impulses=[g.Impulse(burn_time, dv)])
    post = next(sample for sample in actual if sample.time_s == burn_time)
    assert post.position_km == pytest.approx(prior.position_km, abs=1e-9)
    assert post.velocity_km_s == pytest.approx(tuple(v+d for v,d in zip(prior.velocity_km_s,dv)), abs=2e-14)
    # Independent restart at the burn epoch checks integrator synchronization.
    from datetime import datetime, timedelta
    epoch = datetime.fromisoformat(EPOCH.replace('Z','+00:00')) + timedelta(seconds=burn_time)
    expected = g.propagate(post.state, epoch, [120], forces=POINT)[0]
    assert actual[-1].state == pytest.approx(expected.state, rel=0, abs=3e-8)


@extended
def test_coincident_burns_duplicate_samples_and_per_spacecraft_isolation():
    burns = [g.Impulse(60, (0,.01,0)), g.Impulse(60, (0,0,.02))]
    actual = g.propagate_many({"burned": STATE,"quiet":STATE}, EPOCH,[60,60,120],
                              forces=POINT, impulses={"burned":burns})
    baseline = g.propagate(STATE,EPOCH,[60,120],forces=POINT)
    assert actual['quiet'][0].state == pytest.approx(baseline[0].state,abs=1e-9)
    assert actual['quiet'][-1].state == pytest.approx(baseline[-1].state,abs=1e-9)
    assert actual['burned'][0] == actual['burned'][1]
    assert actual['burned'][0].velocity_km_s == pytest.approx(
        tuple(a+b for a,b in zip(baseline[0].velocity_km_s,(0,.01,.02))), abs=1e-12)


@extended
def test_vnb_burn_uses_velocity_direction():
    before = g.propagate(STATE,EPOCH,[600],forces=POINT)[0]
    after = g.propagate_mission(STATE,EPOCH,[600],forces=POINT,
                                impulses=[g.Impulse(600,(.01,0,0),frame='VNB')])[0]
    speed = math.hypot(*before.velocity_km_s)
    delta = tuple(a-b for a,b in zip(after.velocity_km_s,before.velocity_km_s))
    assert delta == pytest.approx(tuple(.01*v/speed for v in before.velocity_km_s),abs=1e-13)


@extended
@pytest.mark.parametrize('target',[6800.,7200.,8000.])
def test_differential_corrector_matches_analytic_instantaneous_burn(target):
    result = g.target_sma(STATE,EPOCH,target)
    expected = math.sqrt(MU*(2/7000-1/target))-STATE[4]
    assert result.delta_v_km_s == pytest.approx(expected,abs=2e-9)
    assert abs(result.residual_km) <= 1e-5
    energy = sum(v*v for v in result.final_state[3:])/2 - MU/math.hypot(*result.final_state[:3])
    assert -MU/(2*energy) == pytest.approx(target,abs=1e-5)


@extended
def test_unconverged_target_raises_and_next_operation_recovers():
    with pytest.raises(RuntimeError,match='converge|complete'):
        g.target_sma(STATE,EPOCH,20000,max_iterations=1,tolerance_km=1e-10)
    assert len(g.propagate(STATE,EPOCH,[0],forces=POINT)) == 1


@extended
def test_core_script_result_is_copied_and_cleanup_follows_error(tmp_path):
    script = tmp_path/'mission.script'
    script.write_text('Create Spacecraft Sat;\nBeginMissionSequence;\nSat.X = 7100;\n')
    result = g.run_script(script,outputs={'Sat':['X']})
    assert float(result['Sat']['X']) == 7100
    with g.native_session() as api:
        assert api.Moderator.Instance().GetConfiguredObject('Sat') is None
    with pytest.raises(ValueError,match='not found'):
        g.run_script(script,outputs={'Missing':['X']})
    assert g.run_script(script,outputs={'Sat':['X']}) == result


def test_minimal_reports_missing_workflows_before_native_work():
    if g.capabilities().profile != 'minimal':
        pytest.skip('minimal profile only')
    for fn,args in [(g.propagate_many,({},EPOCH,[])),
                    (g.propagate_mission,(STATE,EPOCH,[0])),
                    (g.target_sma,(STATE,EPOCH,7200)),
                    (g.run_script,('absent.script',))]:
        with pytest.raises(g.UnsupportedCapabilityError,match='extended'):
            fn(*args,**({'outputs':{}} if fn is g.run_script else {}))
    assert not g.capabilities().supports('spice_kernels')


@extended
@pytest.mark.parametrize('kwargs',[
    {'impulses':{'missing':[g.Impulse(0,(0,0,0))]}},
    {'impulses':{'sat':[g.Impulse(100,(0,0,0))]}},
    {'spacecraft':{'sat':object()}},
    {'accuracy':float('nan')}, {'max_step_s':0},
])
def test_invalid_mission_inputs_do_not_poison_engine(kwargs):
    with pytest.raises((ValueError,TypeError)):
        g.propagate_many({'sat':STATE},EPOCH,[0],**kwargs)
    assert len(g.propagate(STATE,EPOCH,[0],forces=POINT)) == 1


@extended
def test_multi_spacecraft_preserves_individual_srp_properties():
    forces = g.ForceModel(degree=0, sun=False, moon=False, srp=True)
    props = {'light':g.Spacecraft(mass_kg=100,srp_area_m2=20),
             'heavy':g.Spacecraft(mass_kg=1000,srp_area_m2=2)}
    actual = g.propagate_many({name:STATE for name in props},EPOCH,[600],forces=forces,spacecraft=props)
    for name in props:
        expected = g.propagate(STATE,EPOCH,[600],forces=forces,spacecraft=props[name])[0]
        assert actual[name][0].state == pytest.approx(expected.state,rel=0,abs=2e-8)
    assert math.dist(actual['light'][0].position_km,actual['heavy'][0].position_km) > 1e-6
