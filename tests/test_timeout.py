import subprocess
import sys
import time
import unittest
from pathlib import Path


RUNNER = Path(__file__).parents[1] / "scripts" / "run_with_timeout.py"


class TimeoutRunnerTests(unittest.TestCase):
    def test_returns_successful_command_output(self):
        result = subprocess.run(
            [sys.executable, str(RUNNER), "2", sys.executable, "-c", "print('ready')"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "ready")

    def test_terminates_a_stuck_command(self):
        started = time.monotonic()
        result = subprocess.run(
            [sys.executable, str(RUNNER), "0.1", sys.executable, "-c", "import time; time.sleep(10)"],
            capture_output=True,
            text=True,
            check=False,
        )
        elapsed = time.monotonic() - started
        self.assertEqual(result.returncode, 124)
        self.assertLess(elapsed, 2)


if __name__ == "__main__":
    unittest.main()
