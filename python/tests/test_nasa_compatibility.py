"""Compatibility checks for deliberately retained NASA native API quirks."""

import subprocess
import sys


def test_startup_path_getter_retains_nasa_cwd_side_effect(tmp_path):
    # NASA's full-path getter uses the caller's current directory and mutates
    # the saved startup directory. It can therefore report a nonexistent file.
    # Exercise that compatibility behavior in a child: the real engine's
    # singleton state and the changed cwd must not affect other package tests.
    code = r'''
import os
from pathlib import Path
import sys
import tempfile

from gmatpy import native_session, _runtime

original_cwd = Path.cwd()
with native_session() as api:
    # Bootstrap still preserves cwd and reads its actual private startup file.
    assert Path.cwd() == original_cwd
    manager = api.FileManager.Instance()
    initialized_directory = Path(manager.GetStartupFileDir()).resolve()
    assert initialized_directory == Path(_runtime._directory.name).resolve()
    startup_name = manager.GetStartupFileName()
    assert startup_name == "startup.txt"
    assert (initialized_directory / startup_name).is_file()

    with tempfile.TemporaryDirectory(prefix="caller-cwd-", dir=sys.argv[1]) as directory:
        try:
            os.chdir(directory)
            expected_directory = str(Path.cwd()) + manager.GetPathSeparator()
            assert Path.cwd() != initialized_directory
            assert not (Path.cwd() / startup_name).exists()

            reported = manager.GetFullStartupFilePath()
            assert reported == expected_directory + startup_name
            assert manager.GetStartupFileDir() == expected_directory
            # This is the known native quirk, not the actual loaded file's path.
            assert not Path(reported).exists()
            assert (initialized_directory / startup_name).is_file()
        finally:
            os.chdir(original_cwd)

assert Path.cwd() == original_cwd
print("NASA_STARTUP_GETTER_COMPATIBLE")
'''
    result = subprocess.run(
        [sys.executable, "-I", "-c", code, str(tmp_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "NASA_STARTUP_GETTER_COMPATIBLE" in result.stdout
