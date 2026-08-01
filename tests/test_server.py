import json
import subprocess
import unittest
from unittest.mock import patch

import server


class CollectionTests(unittest.TestCase):
    def setUp(self):
        server._cache = {"ts": 0.0, "data": None}
        server._last_good.clear()

    @patch("server.find_collector", return_value=["fake-cclimits"])
    @patch("server.subprocess.run")
    def test_collects_json(self, run, _collector):
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({"claude": {"status": "ok"}}), stderr=""
        )
        result = server.collect(force=True)
        self.assertEqual(result["claude"]["status"], "ok")
        self.assertIn("_collected_at", result)

    @patch("server.find_collector", return_value=["fake-cclimits"])
    @patch("server.subprocess.run")
    def test_reports_collector_failure(self, run, _collector):
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=2, stdout="", stderr="provider request failed"
        )
        result = server.collect(force=True)
        self.assertIn("cclimits exited with status 2", result["_error"])


if __name__ == "__main__":
    unittest.main()
