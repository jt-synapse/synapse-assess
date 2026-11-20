import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sb001_ready", HERE / "ready.py")
ready = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ready)


class ReadyTests(unittest.TestCase):
    def test_only_matching_workloads_return_the_required_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory) / "profile"
            for workload in ("minimal", "orderflow", "interactive"):
                profile.write_text("minimal" if workload == "minimal" else "orderflow")
                output = io.StringIO()
                with (
                    patch.object(ready, "PROFILE", profile),
                    patch.object(sys, "argv", ["ready", workload]),
                    patch.object(ready, "check_workspace") as fs,
                    patch.object(ready, "check_database") as db,
                    patch.object(ready, "check_application") as api,
                    contextlib.redirect_stdout(output),
                ):
                    ready.main()
                fs.assert_called_once_with()
                self.assertEqual(db.call_count, workload != "minimal")
                self.assertEqual(api.call_count, workload != "minimal")
                self.assertEqual(output.getvalue(), f"SB001_READY {workload}\n")
            profile.write_text("minimal")
            with (
                patch.object(ready, "PROFILE", profile),
                patch.object(sys, "argv", ["ready", "orderflow"]),
                self.assertRaisesRegex(RuntimeError, "does not match"),
            ):
                ready.main()

    def test_failed_database_cannot_emit_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory) / "profile"
            profile.write_text("orderflow")
            output = io.StringIO()
            with (
                patch.object(ready, "PROFILE", profile),
                patch.object(sys, "argv", ["ready", "interactive"]),
                patch.object(ready, "check_workspace"),
                patch.object(
                    ready, "check_database", side_effect=RuntimeError("database unavailable")
                ),
                patch.object(ready, "check_application") as api,
                contextlib.redirect_stdout(output),
                self.assertRaisesRegex(RuntimeError, "unavailable"),
            ):
                ready.main()
            api.assert_not_called()
            self.assertEqual(output.getvalue(), "")
