import json
import re
import subprocess
import sys
import tarfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parents[1]


class ContextTests(unittest.TestCase):
    def test_all_workloads_use_pinned_images_and_expected_candidate_files(self):
        with TemporaryDirectory() as directory:
            hashes = {}
            for profile in ("minimal", "orderflow", "interactive"):
                context = Path(directory) / profile
                result = subprocess.run(
                    [sys.executable, HERE / "prepare.py", profile, context],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                summary = json.loads(result.stdout)
                self.assertEqual(profile, summary["workload"])
                files = {p.name for p in context.iterdir()}
                dockerfile = (context / "Dockerfile").read_text()
                for image in re.findall(r"^FROM (\S+)", dockerfile, re.MULTILINE):
                    self.assertRegex(image, r"@sha256:[0-9a-f]{64}$")
                self.assertIn("COPY --chmod=0555 ready.py /opt/sb001/ready", dockerfile)
                if profile == "minimal":
                    self.assertEqual(files, {"Dockerfile", "ready.py"})
                    self.assertNotIn("postgres", dockerfile.lower())
                else:
                    self.assertEqual(
                        files, {"Dockerfile", "ready.py", "candidate.tar", "postgres_service.py"}
                    )
                    hashes[profile] = summary["candidate_sha256"]
                    with tarfile.open(context / "candidate.tar") as public:
                        self.assertIn("orderflow/main.py", public.getnames())
                        self.assertTrue(all(member.isfile() for member in public))
                        for name in public.getnames():
                            self.assertFalse(
                                {"evaluator", "hidden", "reference", "instructions"}
                                & set(Path(name).parts)
                            )
            self.assertEqual(hashes["interactive"], hashes["orderflow"])


if __name__ == "__main__":
    unittest.main()
