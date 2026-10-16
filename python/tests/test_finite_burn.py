"""Core-script finite thrust and propellant depletion, no optional plugin."""
from pathlib import Path
import math
import pytest
import gmatpy as g

@pytest.mark.skipif(g.capabilities().profile != 'extended', reason='extended-profile workflow')
def test_finite_burn_matches_thrust_and_mass_flow(tmp_path):
    fields=['X','Y','Z','VX','VY','VZ','TotalMass']
    base='''Create Spacecraft Sat;
    Sat.DateFormat = UTCGregorian;
    Sat.Epoch = '20 Jul 2020 12:00:00.000';
    Sat.CoordinateSystem = EarthMJ2000Eq;
    Sat.DisplayStateType = Cartesian;
    Sat.X = 7000; Sat.Y = 0; Sat.Z = 0;
    Sat.VX = 0; Sat.VY = 7.546053287267836; Sat.VZ = 0;
    Sat.DryMass = 1000;
    Create ChemicalTank Tank;
    Tank.FuelMass = 10;
    Create ChemicalThruster Thrust;
    Thrust.CoordinateSystem = Local;
    Thrust.Origin = Earth;
    Thrust.Axes = MJ2000Eq;
    Thrust.ThrustDirection1 = 0;
    Thrust.ThrustDirection2 = 1;
    Thrust.ThrustDirection3 = 0;
    Thrust.Tank = {Tank};
    Thrust.DecrementMass = true;
    Thrust.C1 = 1;
    Thrust.K1 = 300;
    Sat.Tanks = {Tank};
    Sat.Thrusters = {Thrust};
    Create FiniteBurn Burn;
    Burn.Thrusters = {Thrust};
    Create ForceModel Forces;
    Forces.CentralBody = Earth;
    Forces.PrimaryBodies = {Earth};
    Forces.PointMasses = {};
    Forces.Drag = None;
    Forces.SRP = Off;
    Forces.RelativisticCorrection = Off;
    Forces.GravityField.Earth.Degree = 0;
    Forces.GravityField.Earth.Order = 0;
    Forces.GravityField.Earth.PotentialFile = 'GRAVITY';
    Create Propagator Prop;
    Prop.FM = Forces;
    Prop.Type = PrinceDormand78;
    Prop.Accuracy = 1e-12;
    Prop.InitialStepSize = 1;
    Prop.MaxStep = 1;
    BeginMissionSequence;
    '''.replace('; Sat.',';\nSat.').replace('GRAVITY',str(Path(g.__file__).resolve().parent/'data/gravity/earth/EGM96.cof'))
    results = []
    script = tmp_path/'finite.script'
    for active in (False, True):
        script.write_text(base+('BeginFiniteBurn Burn(Sat);\n' if active else '')+
                          'Propagate Prop(Sat) {Sat.ElapsedSecs = 10};\n'+
                          ('EndFiniteBurn Burn(Sat);\n' if active else ''))
        results.append({key:float(value) for key,value in g.run_script(script,outputs={'Sat':fields})['Sat'].items()})
    baseline, burned = results
    # Native ChemicalThruster's default gravitational acceleration is 9.81 m/s².
    expected_mass = 1010 - 10/(300*9.81)
    assert burned['TotalMass'] == pytest.approx(expected_mass,abs=2e-9)
    expected_dv = 300*9.81*math.log(1010/expected_mass)/1000
    assert burned['VY']-baseline['VY'] == pytest.approx(expected_dv,abs=2e-9)
    assert burned['Y'] > baseline['Y']
    assert baseline['TotalMass'] == 1010
