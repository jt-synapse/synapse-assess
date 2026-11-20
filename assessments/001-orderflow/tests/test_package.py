import hashlib
import json
import shutil
import tarfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from package import PRIVATE_FILES, PUBLIC_FILES, ROOT, build_candidate, build_release


class PackageTests(unittest.TestCase):
    def test_release_digests_bind_artifacts_and_stage_briefs(self):
        with TemporaryDirectory() as directory:
            release = Path(directory) / "release"
            digest = "sha256:" + "a" * 64
            build_release(release, digest)
            manifest = json.loads((release / "manifest.yaml").read_text())
            self.assertEqual(manifest["runtime"]["image_digest"], digest)
            for field, names in (
                ("candidate_artifact", PUBLIC_FILES),
                ("evaluator_artifact", PRIVATE_FILES),
            ):
                artifact = manifest[field]
                path = release / artifact["path"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])
                with tarfile.open(path) as bundle:
                    self.assertEqual(bundle.getnames(), list(names))
            for stage in manifest["stages"]:
                brief = release / stage["instructions_path"]
                self.assertEqual(
                    hashlib.sha256(brief.read_bytes()).hexdigest(), stage["instructions_sha256"]
                )
            with self.assertRaises(FileExistsError):
                build_release(release, digest)

    def test_public_archive_is_reproducible_and_excludes_private_files(self):
        with TemporaryDirectory() as directory:
            work = Path(directory)
            copy = work / "candidate"
            shutil.copytree(ROOT / "candidate", copy)
            (copy / "private-notes.md").write_text("canary")
            first = build_candidate(copy, work / "first.tar")
            self.assertEqual(first, build_candidate(copy, work / "second.tar"))
            with tarfile.open(work / "first.tar") as archive:
                self.assertEqual(archive.getnames(), list(PUBLIC_FILES))
                self.assertTrue(all(entry.isfile() for entry in archive))
                self.assertNotIn("private-notes.md", archive.getnames())

    def test_allowlisted_names_cannot_be_replaced_by_links(self):
        with TemporaryDirectory() as directory:
            work = Path(directory)
            copy = work / "candidate"
            shutil.copytree(ROOT / "candidate", copy)
            (copy / "README.md").unlink()
            (copy / "README.md").symlink_to(ROOT / "evaluator" / "review.md")
            with self.assertRaises(ValueError):
                build_candidate(copy, work / "unsafe.tar")
            self.assertFalse((work / "unsafe.tar").exists())

    def test_manifest_has_expected_protocol_and_disjoint_artifacts(self):
        manifest = json.loads((ROOT / "manifest.yaml").read_text())
        self.assertEqual(
            [(stage["duration_minutes"], stage["ai_enabled"]) for stage in manifest["stages"]],
            [(35, False), (40, True), (15, False)],
        )
        self.assertEqual(manifest["services"], ["postgresql"])
        for field in ("candidate_artifact", "evaluator_artifact"):
            self.assertTrue((ROOT / manifest[field]["path"]).is_dir())
        self.assertNotEqual(
            manifest["candidate_artifact"]["path"], manifest["evaluator_artifact"]["path"]
        )


if __name__ == "__main__":
    unittest.main()
