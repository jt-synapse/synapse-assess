import json
from pathlib import Path
from uuid import uuid4

import pytest

from benchmarks.sb001.report import Attempt, read_attempts, summarize


def row(**changes):
    return {
        "run_id": str(uuid4()),
        "provider": "e2b",
        "profile": "standard",
        "workload": "minimal",
        "region": "fixture",
        "start_kind": "cold",
        "sdk_version": "test",
        "image_digest": "sha256:" + "0" * 64,
        "ready_ms": 300,
        "terminate_ms": 10,
        "completed": True,
        "cleanup_verified": True,
        **changes,
    }


def summary(rows):
    return summarize(Attempt.from_record(data) for data in rows)


def test_reports_nearest_rank_without_mixing_configurations():
    rows = [row(ready_ms=i) for i in range(1, 31)] + [row(start_kind="warm")]
    cold, warm = summary(rows)
    assert cold["readiness"] == {"samples": 30, "median_ms": 15.5, "p95_ms": 29, "max_ms": 30}
    assert cold["lifecycle_targets_met"]
    assert warm["attempts"] == 1
    assert not warm["lifecycle_targets_met"]


def test_failures_and_missing_cleanup_are_counted():
    rows = [row() for _ in range(30)]
    rows.append(row(ready_ms=None, terminate_ms=None, completed=False, cleanup_verified=False))
    (result,) = summary(rows)
    assert result["incomplete_fraction"] == 1 / 31
    assert result["cleanup_unverified"] == 1
    assert result["readiness"]["samples"] == 30
    assert not result["lifecycle_targets_met"]


@pytest.mark.parametrize(
    "changes",
    [
        {"ready_ms": float("nan")},
        {"ready_ms": -1},
        {"terminate_ms": True},
        {"cleanup_verified": "true"},
        {"image_digest": "latest"},
        {"completed": True, "ready_ms": None},
    ],
)
def test_rejects_invalid_observations(changes):
    with pytest.raises((ValueError, TypeError)):
        Attempt.from_record(row(**changes))


def test_duplicate_run_cannot_boost_sample_count(tmp_path: Path):
    data = json.dumps(row()) + "\n"
    source = tmp_path / "rows.jsonl"
    source.write_text(data * 2)
    with pytest.raises(ValueError, match=r"rows.jsonl:2: duplicate run_id"):
        list(read_attempts([source]))
