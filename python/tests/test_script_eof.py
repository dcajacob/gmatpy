"""Bounded installed-engine regression for unsigned-char stream EOF handling."""

import subprocess
import sys

import pytest


@pytest.mark.parametrize("ending", [b"\n", b"\r\n", b""])
def test_native_script_reader_reaches_eof(tmp_path, ending):
    # Linux AArch64's unsigned plain char previously narrowed EOF to 255 and
    # hung in ReadFirstPass, before any mission command or propagation ran.
    # A subprocess timeout makes that regression bounded on every installed wheel.
    script = tmp_path / "eof.script"
    separator = b"\r\n" if ending == b"\r\n" else b"\n"
    script.write_bytes(
        b"Create Spacecraft EofSat;" + separator
        + b"BeginMissionSequence;" + ending
    )
    code = """
import sys
from gmatpy import native_session
with native_session() as api:
    assert api.LoadScript(sys.argv[1])
    sat = api.GetObject('EofSat')
    assert sat.GetTypeName() == 'Spacecraft'
    assert sat.GetName() == 'EofSat'
print('SCRIPT_EOF_OK')
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code, str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SCRIPT_EOF_OK" in result.stdout
