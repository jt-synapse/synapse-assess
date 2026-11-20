"""Run and reconcile bounded synthetic sandbox attempts, preserving every measurement."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import time
from contextlib import ExitStack
from dataclasses import asdict
from itertools import combinations
from pathlib import Path
from typing import Any, TextIO
from uuid import UUID, uuid4

from .drivers import PINS, TTL_SECONDS, Driver, Workload, load_driver


def _row(config: Workload, run_id: str) -> dict[str, Any]:
    fields = asdict(config)
    fields.pop("template")
    return dict(
        fields,
        sdk_version=PINS[config.provider],
        run_id=run_id,
        ready_ms=None,
        terminate_ms=None,
        completed=False,
        cleanup_verified=False,
    )


def _journal(stream: TextIO, event: str, **values: Any) -> None:
    stream.write(json.dumps({"event": event, **values}) + "\n")
    stream.flush()
    os.fsync(stream.fileno())


def _repair_trailing_write(stream: TextIO) -> None:
    """Caller holds the file lock. Preserve torn bytes before recovering the preceding records."""
    stream.flush()
    fd = stream.fileno()
    size = os.fstat(fd).st_size
    if not size or os.pread(fd, 1, size - 1) == b"\n":
        return
    start = size
    while start:
        offset = max(0, start - 4096)
        block = os.pread(fd, start - offset, offset)
        previous = block.rfind(b"\n")
        if previous >= 0:
            start = offset + previous + 1
            break
        start = offset
    tail = os.pread(fd, size - start, start)
    try:
        json.loads(tail)
    except (ValueError, UnicodeDecodeError):
        backup = Path(stream.name + f".{uuid4()}.partial")
        with backup.open("xb") as saved:
            saved.write(tail)
            saved.flush()
            os.fsync(saved.fileno())
        stream.truncate(start)
    else:
        stream.seek(0, os.SEEK_END)
        stream.write("\n")
    stream.flush()
    os.fsync(fd)
    stream.seek(0, os.SEEK_END)


def _append(stream: TextIO, record: dict[str, Any], *, check_existing: bool = False) -> None:
    local_file = hasattr(stream, "name")
    if local_file:
        fcntl.flock(stream, fcntl.LOCK_EX)
    try:
        if local_file:
            _repair_trailing_write(stream)
        if check_existing:
            stream.seek(0)
            if any(
                json.loads(line)["run_id"] == record["run_id"] for line in stream if line.strip()
            ):
                return
        stream.seek(0, os.SEEK_END)
        stream.write(json.dumps(record) + "\n")
        stream.flush()
        if local_file:
            os.fsync(stream.fileno())
    finally:
        if local_file:
            fcntl.flock(stream, fcntl.LOCK_UN)


def measure(
    config: Workload,
    driver: Driver,
    output: TextIO,
    detail: TextIO | None = None,
    *,
    run_id: str | None = None,
    journal: TextIO | None = None,
) -> bool:
    if detail is not None and config.workload != "interactive":
        raise ValueError("long-running PTY probe requires the interactive workload")
    ttl = 7200 if detail is not None else TTL_SECONDS
    run_id = run_id or str(uuid4())
    record = _row(config, run_id)
    if journal:
        _journal(journal, "intent", run_id=run_id, config=asdict(config), ttl_seconds=ttl)
    print(f"Starting SB-001 run {run_id}", file=sys.stderr, flush=True)
    sandbox = None
    started = time.monotonic()
    try:
        sandbox = driver.create(config, run_id, ttl_seconds=ttl)
        if journal:
            provider_id = sandbox.sandbox_id if config.provider == "e2b" else sandbox.id
            _journal(journal, "allocated", sandbox_id=provider_id)
        driver.probe(sandbox, config, ttl_seconds=ttl)
        record["ready_ms"] = (time.monotonic() - started) * 1000
        if detail is not None:
            from .interactive import run_interactive

            run_interactive(sandbox, config.provider, run_id, detail)
        record["completed"] = True
    except Exception as exc:  # noqa: BLE001 - provider diagnostic text can contain secrets
        print(f"{run_id} probe failed ({type(exc).__name__})", file=sys.stderr)
    finally:
        terminating = time.monotonic()
        try:
            record["cleanup_verified"] = driver.cleanup(sandbox, run_id)
            if record["cleanup_verified"]:
                record["terminate_ms"] = (time.monotonic() - terminating) * 1000
        except Exception as exc:  # noqa: BLE001 - retain the incomplete attempt after any SDK failure
            print(f"{run_id} deletion unverified ({type(exc).__name__})", file=sys.stderr)
        finally:
            if journal:
                _journal(journal, "outcome", row=record)
            _append(output, record)
    return record["completed"] and record["cleanup_verified"]


def reconcile(
    config: Workload, driver: Driver, output: TextIO, journal: TextIO, run_id: str
) -> bool:
    _repair_trailing_write(journal)
    journal.seek(0)
    history = [json.loads(line) for line in journal]
    if not history or history[0].get("event") != "intent" or history[0].get("run_id") != run_id:
        raise ValueError("journal does not identify this run")
    if history[0]["config"] != asdict(config):
        raise ValueError("benchmark configuration differs from the recorded intent")
    known_id = next(
        (entry["sandbox_id"] for entry in history if entry["event"] == "allocated"), None
    )
    outcome = next((entry["row"] for entry in history if entry["event"] == "outcome"), None)
    prior = next(
        (
            entry
            for entry in reversed(history)
            if entry["event"] == "reconciled" and entry["verified"]
        ),
        None,
    )
    if outcome and outcome["cleanup_verified"] or prior:
        verified = True
    else:
        started = time.monotonic()
        try:
            verified = driver.recover(run_id, known_id)
        except Exception as exc:  # noqa: BLE001 - record recovery failures without provider diagnostics
            print(f"{run_id} recovery unverified ({type(exc).__name__})", file=sys.stderr)
            verified = False
        _journal(
            journal,
            "reconciled",
            verified=verified,
            recovery_ms=(time.monotonic() - started) * 1000,
        )
    # Reconciliation can establish present absence after lease expiry. It cannot reconstruct
    # the original termination latency, so a missing outcome remains an incomplete run.
    _append(output, outcome or _row(config, run_id), check_existing=True)
    return verified


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "config", type=Path, help="JSON mapping of immutable template release to workload"
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--measure",
        metavar="JSONL",
        type=Path,
        help="provision one billable sandbox and append the measurement",
    )
    actions.add_argument(
        "--reconcile", metavar="JSONL", type=Path, help="recover cleanup for a journaled run"
    )
    parser.add_argument("--run-id", type=UUID, help="run to recover with --reconcile")
    parser.add_argument(
        "--interactive-detail",
        type=Path,
        metavar="JSONL",
        help="measure 110-minute interactive longevity and PTY behavior with a two-hour lease",
    )
    args = parser.parse_args()
    try:
        job = Workload(**json.loads(args.config.read_text()))
    except (OSError, ValueError, TypeError) as exc:
        parser.error(f"Invalid benchmark configuration: {exc}")
    if bool(args.run_id) != bool(args.reconcile):
        parser.error("--reconcile requires --run-id")
    if args.interactive_detail and (not args.measure or job.workload != "interactive"):
        parser.error("--interactive-detail requires --measure and the interactive workload")
    results = args.measure or args.reconcile
    if not results:
        print(f"Valid {job.provider} workload configuration (SDK {PINS[job.provider]}).")
        return
    paths = [args.config, results]
    if args.interactive_detail:
        paths.append(args.interactive_detail)
    for left, right in combinations(paths, 2):
        if left.resolve() == right.resolve() or (
            left.exists() and right.exists() and left.samefile(right)
        ):
            parser.error("configuration, measurements and detail must use distinct files")
    run_id = str(args.run_id or uuid4())
    directory = results.with_name(results.name + ".runs")
    directory.mkdir(exist_ok=True)
    try:
        with ExitStack() as stack:
            journal = stack.enter_context(
                (directory / f"{run_id}.jsonl").open("r+" if args.reconcile else "x+")
            )
            fcntl.flock(journal, fcntl.LOCK_EX | fcntl.LOCK_NB)
            stream = stack.enter_context(results.open("a+", encoding="utf-8"))
            driver = load_driver(job.provider)
            if args.reconcile:
                success = reconcile(job, driver, stream, journal, run_id)
            else:
                detail = (
                    stack.enter_context(args.interactive_detail.open("a"))
                    if args.interactive_detail
                    else None
                )
                success = measure(job, driver, stream, detail, run_id=run_id, journal=journal)
            os.fsync(stream.fileno())
    except (BlockingIOError, FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
