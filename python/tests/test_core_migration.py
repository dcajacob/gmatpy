"""Contracts for focused shared-core fixes retained by the standalone project."""
from pathlib import Path
import subprocess
import sys
import pytest
import gmatpy as g


@pytest.mark.parametrize('kind',['SMADot','TLONGDot'])
def test_native_rate_parameter_factory_reports_requested_type(kind):
    with g.native_session() as api:
        parameter=api.Construct(kind,'Migration'+kind)
        assert parameter.GetTypeName()==kind


def test_ephemeris_output_cannot_replace_a_directory(tmp_path):
    destination=tmp_path/'preserve';destination.mkdir()
    with g.native_session() as api:
        api.Construct('Spacecraft','MigrationSat')
        writer=api.Construct('EphemerisFile','MigrationEphemeris')
        writer.SetField('Spacecraft','MigrationSat')
        writer.SetField('FileFormat','CCSDS-OEM')
        with pytest.raises(api.APIException,match='directory'):
            writer.SetField('Filename',str(destination))
            api.Initialize()
            writer.Initialize()
    assert destination.is_dir()


@pytest.mark.skipif(not g.capabilities().supports('spice_kernels'),reason='extended kernel implementation only')
def test_kernel_failure_and_missing_file_clear_leave_engine_usable(tmp_path):
    # Isolate the process-global kernel pool from the rest of this test suite.
    code='''import pathlib,shutil,sys,math
import gmatpy as g
root=pathlib.Path(sys.argv[1]);kernel=root/'temporary.tls'
shutil.copyfile(pathlib.Path(g.__file__).parent/'data/time/SPICELeapSecondKernel.tls',kernel)
with g.native_session() as api:
 s=api.SpiceInterface()
 try:s.LoadKernel(str(root/'does-not-exist.bsp'))
 except api.APIException:pass
 else:raise AssertionError('Missing kernel accepted')
 assert not s.IsLoaded(str(root/'does-not-exist.bsp'))
 s.LoadKernel(str(kernel));assert s.IsLoaded(str(kernel))
 kernel.unlink();s.UnloadAllKernels();assert not s.IsLoaded(str(kernel))
assert all(math.isfinite(x) for x in g.body_state('Moon','2024-01-01T00:00:00Z'))
print('KERNEL_RECOVERY_OK')
'''
    result=subprocess.run([sys.executable,'-c',code,str(tmp_path)],capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'KERNEL_RECOVERY_OK' in result.stdout
