"""Summarize SB-001 lifecycle measurements without inferring isolation or selection."""

import argparse
import json
import math
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any
from uuid import UUID


@dataclass(frozen=True, order=True)
class Configuration:
    provider: str
    region: str
    profile: str
    workload: str
    image_digest: str
    sdk_version: str
    start_kind: str


@dataclass(frozen=True)
class Attempt:
    run_id: UUID
    configuration: Configuration
    ready_ms: float | None
    terminate_ms: float | None
    completed: bool
    cleanup_verified: bool

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "Attempt":
        config = Configuration(**{key: record[key] for key in Configuration.__annotations__})
        for value in vars(config).values():
            if not isinstance(value, str) or not value.strip():
                raise ValueError("configuration values must be nonempty strings")
        if config.provider not in {"e2b", "daytona"}:
            raise ValueError("unsupported benchmark provider")
        if config.profile not in {"standard", "stress"}:
            raise ValueError("unknown resource profile")
        if config.workload not in {"minimal", "orderflow", "interactive"}:
            raise ValueError("unknown workload")
        if config.start_kind not in {"cold", "warm"}:
            raise ValueError("start_kind must be cold or warm")
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", config.image_digest):
            raise ValueError("a pinned image digest is required")
        completed, cleaned = record["completed"], record["cleanup_verified"]
        if not isinstance(completed, bool) or not isinstance(cleaned, bool):
            raise TypeError("completion and cleanup must be booleans")
        ready = duration(record["ready_ms"])
        terminate = duration(record["terminate_ms"])
        if completed and ready is None:
            raise ValueError("completed attempt requires a readiness measurement")
        if cleaned and terminate is None:
            raise ValueError("verified cleanup requires a termination measurement")
        return cls(UUID(str(record["run_id"])), config, ready, terminate, completed, cleaned)


def duration(value: Any) -> float | None:
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("duration must be a finite nonnegative number of milliseconds or null")
    return float(value)


def read_attempts(paths: list[Path]) -> Iterable[Attempt]:
    seen: set[UUID] = set()
    for path in paths:
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        raise TypeError("expected a JSON object")
                    attempt = Attempt.from_record(record)
                    if attempt.run_id in seen:
                        raise ValueError(f"duplicate run_id {attempt.run_id}")
                except (KeyError, ValueError, TypeError, OverflowError) as exc:
                    raise ValueError(f"{path}:{line_number}: {exc}") from exc
                seen.add(attempt.run_id)
                yield attempt


def latency(values: list[float]) -> dict[str, float | int] | None:
    if not values:
        return None
    ordered = sorted(values)
    return {
        "samples": len(ordered),
        "median_ms": median(ordered),
        "p95_ms": ordered[math.ceil(0.95 * len(ordered)) - 1],
        "max_ms": ordered[-1],
    }


def summarize(attempts: Iterable[Attempt]) -> list[dict[str, Any]]:
    groups: dict[Configuration, list[Attempt]] = defaultdict(list)
    for attempt in attempts:
        groups[attempt.configuration].append(attempt)
    results = []
    for config, group in sorted(groups.items()):
        ready = latency([a.ready_ms for a in group if a.ready_ms is not None])
        terminated = latency([a.terminate_ms for a in group if a.terminate_ms is not None])
        failed = sum(not a.completed for a in group)
        cleanup_pending = sum(not a.cleanup_verified for a in group)
        ready_target = 30_000 if config.start_kind == "cold" else 10_000
        results.append(
            {
                **vars(config),
                "attempts": len(group),
                "incomplete_attempts": failed,
                "incomplete_fraction": failed / len(group),
                "cleanup_unverified": cleanup_pending,
                "readiness": ready,
                "termination": terminated,
                "lifecycle_targets_met": bool(
                    ready
                    and terminated
                    and ready["samples"] >= 30
                    and terminated["samples"] >= 30
                    and ready["p95_ms"] <= ready_target
                    and terminated["p95_ms"] <= 30_000
                    and failed == 0
                    and cleanup_pending == 0
                ),
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("measurements", type=Path, nargs="+", help="JSON Lines from benchmark runs")
    args = parser.parse_args()
    try:
        results = summarize(read_attempts(args.measurements))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"{exc}\n")
    if not results:
        parser.exit(2, "No measured attempts found.\n")
    print(json.dumps(results, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
