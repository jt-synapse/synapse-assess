"""Create the only context to send to the OCI builder."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parents[2] / "assessments" / "001-orderflow"


def prepare(profile: str, output: Path) -> dict[str, str]:
    if profile not in {"minimal", "orderflow", "interactive"}:
        raise ValueError("unknown SB-001 workload")
    if output.exists():
        raise FileExistsError(output)
    is_db = profile != "minimal"
    with TemporaryDirectory(dir=output.parent) as directory:
        context = Path(directory) / "context"
        context.mkdir()
        shutil.copyfile(
            HERE / ("orderflow.Dockerfile" if is_db else "minimal.Dockerfile"),
            context / "Dockerfile",
        )
        shutil.copyfile(HERE / "ready.py", context / "ready.py")
        result = {"workload": profile}
        if is_db:
            shutil.copyfile(HERE / "postgres_service.py", context / "postgres_service.py")
            completed = subprocess.run(
                [sys.executable, PACKAGE / "tests/package.py", context / "candidate.tar"],
                check=True,
                capture_output=True,
                text=True,
            )
            result["candidate_sha256"] = completed.stdout.strip()
        context.rename(output)
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workload", choices=("minimal", "orderflow", "interactive"))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.workload, args.output), sort_keys=True))
