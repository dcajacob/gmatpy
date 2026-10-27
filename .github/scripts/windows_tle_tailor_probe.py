"""Bounded native Windows integration of installed GMAT Py and public TLE Tailor.

JAX is a required CPU dependency. No fallback or optional JAX import is allowed.
Public main's current CLI default is FD; the requested JAX path is tested
explicitly without changing that checkout's code or metadata.
"""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys

import gmatpy
import jax
import jax.numpy as jnp
import numpy as np
from sgp4.exporter import export_tle
from astropy.utils import iers
import tle_tailor
from tle_tailor.propagation.gmatpy import propagate_gmatpy
from tle_tailor.fitting.tlefit_equinoctial_eph_jax import (
    test_tle_fit_normalized_equinoctial as fit_jax,
)
from tle_tailor.examples.scripts.gmat_integration.gmatpy_state_to_tle import state_rms

assert os.name == 'nt'
assert Path(tle_tailor.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
assert Path(gmatpy.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
assert all(device.platform == 'cpu' for device in jax.devices())
assert jax.config.x64_enabled
assert float(jax.jit(lambda x: jnp.sum(x*x))(jnp.array([2., 3.], dtype=jnp.float64))) == 13.
state = [7000., 120., -80., -.2, 7.4, 1.]
epoch = datetime(2024, 1, 1, tzinfo=timezone.utc)
offsets = np.linspace(0., 1800., 25)
with iers.conf.set_temp('auto_download', False):
    times, ephemeris = propagate_gmatpy(state, epoch, offsets)
assert ephemeris.shape == (25, 2, 3) and np.isfinite(ephemeris).all()
result = fit_jax(times, ephemeris, max_iter=5, debug=False)
iterations, satellite, elements, sigma, sigmas = result[:5]
assert 1 <= iterations <= 5 and np.isfinite(elements).all() and np.isfinite(sigma)
assert len(sigmas) >= 2 and sigmas[-1] < sigmas[0], sigmas
assert all(satellite.model.sgp4_tsince(offset)[0] == 0 for offset in (-30., 0.))
line1, line2 = export_tle(satellite.model)
assert line1.startswith('1 ') and line2.startswith('2 ') and len(line1) == len(line2) == 69
position_rms, velocity_rms = state_rms(satellite, times, ephemeris)
assert np.isfinite([position_rms, velocity_rms]).all()
record = {
    'tle_tailor_source': '36be851c2b8c3898cefaf32baad2b2e4e3222f03',
    'python': sys.version,
    'packages': {name: importlib.metadata.version(name) for name in
                 ('gmatpy', 'tle-tailor', 'jax', 'jaxlib', 'numpy', 'scipy', 'astropy', 'pandas')},
    'installed_tle_tailor': str(tle_tailor.__file__), 'installed_gmatpy': str(gmatpy.__file__),
    'jax_devices': [str(device) for device in jax.devices()], 'jax_x64': bool(jax.config.x64_enabled),
    'samples': 25, 'duration_s': 1800., 'fit_method': 'jax', 'iterations': int(iterations),
    'initial_sigma': float(sigmas[0]), 'final_sigma': float(sigmas[-1]),
    'position_rms_km': float(position_rms), 'velocity_rms_km_s': float(velocity_rms),
    'tle': [line1, line2],
    'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'scope': 'Synthetic native propagation -> TEME conversion -> mandatory CPU JAX fit -> valid exported TLE; bounded engineering check, not broad mission accuracy certification.',
}
Path(sys.argv[1]).write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
