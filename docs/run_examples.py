"""Run standalone documentation examples against an already installed gmatpy.

Usage: python docs/run_examples.py
Each example runs in a fresh isolated Python subprocess and temporary directory.
No source-tree path is added and no package is built or installed by this runner.
"""

from pathlib import Path
import subprocess
import sys
import tempfile


EXAMPLES = (
    "quickstart.py",
    "utilities.py",
    "impulses.py",
    "target_sma.py",
    "trusted_script.py",
    "native_session.py",
)


def main():
    examples_dir = Path(__file__).resolve().parent / "examples"
    passed = skipped = failed = 0
    for name in EXAMPLES:
        with tempfile.TemporaryDirectory(prefix="gmatpy-doc-example-") as directory:
            try:
                result = subprocess.run(
                    [sys.executable, "-I", str(examples_dir / name)],
                    cwd=directory,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            except subprocess.TimeoutExpired as error:
                failed += 1
                print(f"FAIL {name}: exceeded 120 s")
                for output in (error.stdout, error.stderr):
                    if output:
                        print(output.decode(errors="replace") if isinstance(output, bytes) else output)
                continue
        if result.returncode:
            failed += 1
            print(f"FAIL {name}: exit status {result.returncode}")
            print(result.stdout + result.stderr)
        elif any(line.startswith("SKIP:") for line in result.stdout.splitlines()):
            skipped += 1
            print(next(line for line in result.stdout.splitlines() if line.startswith("SKIP:")))
        else:
            passed += 1
            print(f"PASS {name}")
    print(f"{passed} passed, {skipped} skipped, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
