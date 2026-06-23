"""Let pytest discover the bare-metal stress suite.

tests/stress_test.py is the primary safety net and runs on the pure standard
library across Python 3.8-3.13 in CI. This wrapper just shells out to it so a
`pytest` run (the dev-only quality job) also exercises it and fails if it fails.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def test_stress_suite_passes():
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "stress_test.py")],
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "all green" in proc.stdout
