"""Bound native API regressions for single-unload priority and explicit reset."""
import subprocess
import sys


def _run_spice_child(code, tmp_path, marker):
    # The kernel pool and native singleton state are process-global. Exercise
    # each failure in a fresh installed-package process, outside the source tree.
    prefix = '''import gmatpy as g
assert g.capabilities().supports("spice_kernels")
'''
    result = subprocess.run([sys.executable, "-I", "-c", prefix + code, str(tmp_path)],
                            cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert marker in result.stdout


def test_failed_individual_unload_preserves_priority_then_explicit_reset_recovers(tmp_path):
    code = r'''
from pathlib import Path
import sys

root = Path(sys.argv[1])
alias = "GMATPY_CLEANUP_REVIEW"
def kernel(name, assignment):
    path = root / name
    path.write_text("KPL/PCK\n\\begindata\n" + assignment + "\n\\begintext\n", encoding="ascii")
    return path

low = kernel("z-low.tpc", "NAIF_BODY_NAME = ( '" + alias + "' )\nNAIF_BODY_CODE = ( 1111111 )")
high = kernel("a-high.tpc", "NAIF_BODY_NAME = ( '" + alias + "' )\nNAIF_BODY_CODE = ( 2222222 )")
missing = kernel("m-missing.tpc", "GMATPY_UNRELATED = ( 3 )")
target = kernel("n-target.tpc", "GMATPY_UNRELATED = ( 4 )")
with g.native_session() as api:
    spice = api.SpiceInterface()
    try:
        for path in (low, high, missing, target):
            assert spice.LoadKernel(str(path))
        assert spice.GetNaifID(alias, False) == 2222222
        missing.unlink()
        # NASA warns and returns true after this reread failure. It must not
        # globally clear and replay unrelated kernels in lexical filename order.
        assert spice.UnloadKernel(str(target))
        assert spice.GetNaifID(alias, False) == 2222222
        assert not spice.IsLoaded(str(target))
    finally:
        # Individual failure does not guarantee reconstructed usable state.
        # The vanished m-file sorts after surviving a-high: this full reset must
        # work without rereading it, rather than depend on a lucky unload order.
        assert spice.UnloadAllKernels()
    for path in (low, high, missing, target):
        assert not spice.IsLoaded(str(path))
    assert spice.GetNaifID(alias, False) == 0

assert all(abs(value) < 1e10 for value in g.body_state("Moon", "2024-01-01T00:00:00Z"))
print("SPICE_SINGLE_UNLOAD_PRIORITY_AND_EXPLICIT_RESET_OK")
'''
    _run_spice_child(code, tmp_path, "SPICE_SINGLE_UNLOAD_PRIORITY_AND_EXPLICIT_RESET_OK")


def test_explicit_reset_removes_untracked_partial_meta_kernel_state(tmp_path):
    code = r'''
from pathlib import Path
import sys

root = Path(sys.argv[1])
alias = "GMATPY_UNTRACKED_REVIEW"
child = root / "orphan.tpc"
child.write_text("KPL/PCK\n\\begindata\nNAIF_BODY_NAME = ( '" + alias +
                 "' )\nNAIF_BODY_CODE = ( 3333333 )\n\\begintext\n", encoding="ascii")
meta = root / "partial.tm"
# Relative child names are valid here because the subprocess's cwd is root.
meta.write_text("KPL/MK\n\\begindata\nKERNELS_TO_LOAD = ( 'orphan.tpc', 'absent-child.tpc' )\n\\begintext\n",
                encoding="ascii")
with g.native_session() as api:
    spice = api.SpiceInterface()
    try:
        try:
            spice.LoadKernel(str(meta))
        except api.APIException:
            pass
        else:
            raise AssertionError("Meta-kernel with a missing child was accepted")
        # FURNSH retains the successful child before reporting the next failure;
        # GMAT never cached the failed meta load or its individual child.
        assert not spice.IsLoaded(str(meta))
        assert not spice.IsLoaded(str(child))
        assert spice.GetNaifID(alias, False) == 3333333
    finally:
        assert spice.UnloadAllKernels()
    assert spice.GetNaifID(alias, False) == 0

assert all(abs(value) < 1e10 for value in g.body_state("Moon", "2024-01-01T00:00:00Z"))
print("SPICE_EXPLICIT_RESET_REMOVES_UNTRACKED_META_STATE_OK")
'''
    _run_spice_child(code, tmp_path, "SPICE_EXPLICIT_RESET_REMOVES_UNTRACKED_META_STATE_OK")
