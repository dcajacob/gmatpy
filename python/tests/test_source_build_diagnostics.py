"""Exercise source-build dependency failures without building the native engine."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


MODULE = Path(__file__).resolve().parents[1] / "cmake/CheckSourceDependencies.cmake"


class SourceDependencies(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gmatpy source check ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.module = self.root / "python/cmake/CheckSourceDependencies.cmake"
        self.module.parent.mkdir(parents=True)
        shutil.copyfile(MODULE, self.module)
        self.fixture = self.root / "probe"
        self.fixture.mkdir()
        (self.fixture / "CMakeLists.txt").write_text(
            'cmake_minimum_required(VERSION 3.19)\nproject(Probe NONE)\n'
            'set(CMAKE_SIZEOF_VOID_P 8)\n'
            f'include("{self.module.as_posix()}")\n'
            'gmatpy_check_source_dependencies()\nmessage(STATUS "PREFLIGHT_PASSED")\n')

    def tree(self, relative="external cspice", omit=()):
        root = self.root / relative
        for name in ("include/SpiceUsr.h", "include/f2c.h", "lib/cspice.a"):
            if name not in omit:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Existence-only dependency fixture; not a native library.\n")
        return root

    def configure(self, definitions=(), environment=None):
        env = os.environ.copy()
        env.pop("CSPICE_DIR", None)
        env.pop("F2C_DIR", None)
        env.update(environment or {})
        result = subprocess.run(["cmake", "-S", str(self.fixture), "-B", str(self.root / "build"),
                                 *["-D" + item for item in definitions]],
                                env=env, capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout + result.stderr

    def assert_missing(self, definitions=(), environment=None):
        code, output = self.configure(definitions, environment)
        self.assertNotEqual(code, 0, output)
        self.assertIn("GMAT Py source-build dependency missing", output)
        self.assertIn("uv python pin 3.14", output)
        self.assertIn("cmake.define.CSPICE_DIR", output)
        self.assertNotIn('The "debug" argument', output)
        self.assertNotIn("Matlab NOT FOUND", output)

    def test_absent_dependency_stops_with_recovery(self):
        self.assert_missing()

    def test_each_missing_component_stops(self):
        for name in ("include/SpiceUsr.h", "include/f2c.h", "lib/cspice.a"):
            with self.subTest(missing=name):
                tree = self.tree(name.replace("/", "-"), omit=(name,))
                self.assert_missing([f"CSPICE_DIR={tree}"])

    def test_complete_tree_and_path_with_spaces(self):
        code, output = self.configure([f"CSPICE_DIR={self.tree()}"])
        self.assertEqual(code, 0, output)
        self.assertIn("PREFLIGHT_PASSED", output)

    def test_environment_path(self):
        code, output = self.configure(environment={"CSPICE_DIR": str(self.tree())})
        self.assertEqual(code, 0, output)

    def test_explicit_path_overrides_environment(self):
        self.assert_missing([f"CSPICE_DIR={self.root / 'invalid'}"],
                            {"CSPICE_DIR": str(self.tree())})

    def test_separate_f2c_header(self):
        tree = self.tree(omit=("include/f2c.h",))
        separate = self.root / "separate f2c"
        separate.mkdir()
        (separate / "f2c.h").write_text("test header\n")
        code, output = self.configure([f"CSPICE_DIR={tree}", f"F2C_DIR={separate}"])
        self.assertEqual(code, 0, output)

    def test_separate_f2c_environment(self):
        tree = self.tree(omit=("include/f2c.h",))
        separate = self.root / "separate f2c"
        separate.mkdir()
        (separate / "f2c.h").write_text("test header\n")
        code, output = self.configure(environment={"CSPICE_DIR": str(tree), "F2C_DIR": str(separate)})
        self.assertEqual(code, 0, output)

    def test_invalid_explicit_f2c_stops(self):
        self.assert_missing([f"CSPICE_DIR={self.tree()}", f"F2C_DIR={self.root / 'invalid'}"])

    def test_existing_default_checkout_path(self):
        self.tree("depends/cspice/linux/cspice64")
        code, output = self.configure()
        self.assertEqual(code, 0, output)


if __name__ == "__main__":
    unittest.main()
