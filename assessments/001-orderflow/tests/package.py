"""Build the candidate tar from the reviewed list of public files."""

import argparse
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = (
    "README.md",
    "requirements.txt",
    "orderflow/__init__.py",
    "orderflow/db.py",
    "orderflow/errors.py",
    "orderflow/main.py",
    "orderflow/reservations.py",
    "orderflow/setup.py",
    "migrations/001_reservations.sql",
    "seed.sql",
    "docs/api_contract.md",
    "tests/test_reservations.py",
)
PRIVATE_FILES = (
    "review.md",
    "hidden/__init__.py",
    "hidden/conftest.py",
    "hidden/probes.py",
    "hidden/test_independent.py",
    "hidden/test_assisted.py",
    "reference/stage_a/atomic.py",
    "reference/stage_a/reservations.py",
    "reference/stage_b/002_idempotency.sql",
    "reference/stage_b/reservations.py",
)


def build_archive(source: Path, destination: Path, names: tuple[str, ...]) -> str:
    source = source.resolve(strict=True)
    # Validate all manifest entries before opening the output.
    contents: dict[str, bytes] = {}
    for name in names:
        path = source / name
        if path.resolve(strict=True) != path or not path.is_file():
            raise ValueError(f"Archive entry must be an ordinary file: {name}")
        contents[name] = path.read_bytes()
    with tarfile.open(destination, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, content in contents.items():
            entry = tarfile.TarInfo(name)
            entry.size = len(content)
            entry.mode = 0o644
            archive.addfile(entry, io.BytesIO(content))
    return hashlib.sha256(destination.read_bytes()).hexdigest()


def build_candidate(source: Path, destination: Path) -> str:
    return build_archive(source, destination, PUBLIC_FILES)


def build_release(output: Path, image_digest: str):
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_digest):
        raise ValueError("Supply the published runtime image's sha256 digest")
    if output.exists():
        raise FileExistsError(output)
    with TemporaryDirectory(dir=output.parent) as temporary:
        release = Path(temporary) / "release"
        release.mkdir()
        manifest = json.loads((ROOT / "manifest.yaml").read_text())
        manifest["runtime"]["image_digest"] = image_digest
        for field, items in (
            ("candidate_artifact", PUBLIC_FILES),
            ("evaluator_artifact", PRIVATE_FILES),
        ):
            name = manifest[field]["path"]
            digest = build_archive(ROOT / name, release / f"{name}.tar", items)
            manifest[field] = {"path": f"{name}.tar", "sha256": digest}
        for stage in manifest["stages"]:
            content = (ROOT / stage["instructions_path"]).read_bytes()
            name = f"instructions/{stage['stage_id']}.md"
            destination = release / name
            destination.parent.mkdir(exist_ok=True)
            destination.write_bytes(content)
            stage["instructions_path"] = name
            stage["instructions_sha256"] = hashlib.sha256(content).hexdigest()
        (release / "manifest.yaml").write_text(json.dumps(manifest, indent=2) + "\n")
        release.rename(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--image-digest", help="Build a complete release directory pinned to this runtime image"
    )
    args = parser.parse_args()
    if args.image_digest:
        build_release(args.output, args.image_digest)
    else:
        print(build_candidate(ROOT / "candidate", args.output))
