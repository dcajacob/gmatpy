"""The profile is a compiled/install inventory boundary, not a Python extra."""
import json
from pathlib import Path
import pytest
import gmatpy as g


def test_installed_profile_matches_actual_data():
    root = Path(g.__file__).resolve().parent
    if not (root/'BUILD_PROFILE.json').exists():
        pytest.skip('development overlay; installed profile is tested in wheels')
    info=json.loads((root/'BUILD_PROFILE.json').read_text())
    assert info['profile'] == g.capabilities().profile
    assert info['spice'] == (info['profile']=='extended')
    actual={p.relative_to(root/'data').as_posix() for p in (root/'data').rglob('*') if p.is_file()}
    assert actual == set(info['data_files'])
    assert len(actual) == (9 if info['profile']=='minimal' else 17)
    assert g.capabilities().supports('frame_conversion')
    assert not g.capabilities().supports('estimation')


def test_minimal_native_spice_rejection_preserves_default_ephemeris():
    if g.capabilities().profile != 'minimal':
        pytest.skip('minimal build only')
    with g.native_session() as api:
        assert not hasattr(api,'SpiceOrbitKernelReader')
        solar=api.GetSolarSystem()
        with pytest.raises(api.APIException,match='extended'):
            solar.SetSource('SPICE')
        assert solar.SetSource('DE405')
    assert all(abs(v)<1e10 for v in g.body_state('Moon','2020-07-20T12:00:00Z'))
