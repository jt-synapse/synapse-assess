import io
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from benchmarks.sb001.drivers import PINS, TTL_SECONDS, DaytonaDriver, E2BDriver, Workload
from benchmarks.sb001.report import Attempt
from benchmarks.sb001.run import measure


def config(name="daytona"):
    return Workload(name, "immutable", "us", "standard", "minimal", "sha256:" + "5" * 64, "cold")


@pytest.mark.parametrize("fail_at", [None, "create", "probe", "cleanup"])
def test_measure_records_readiness_and_cleanup_separately(fail_at):
    driver, stream = Mock(), io.StringIO()
    driver.cleanup.return_value = True
    if fail_at:
        getattr(driver, fail_at).side_effect = RuntimeError("sensitive provider diagnostic")
    success = measure(config(), driver, stream)
    (row,) = stream.getvalue().splitlines()
    parsed = Attempt.from_record(json.loads(row))
    assert parsed.configuration.sdk_version == PINS["daytona"]
    assert (parsed.ready_ms is not None) == (fail_at not in {"create", "probe"})
    assert parsed.completed == (fail_at not in {"create", "probe"})
    assert parsed.cleanup_verified == (fail_at != "cleanup")
    assert success == (fail_at is None)
    driver.cleanup.assert_called_once()


def test_ambiguous_allocation_stays_unverified(capsys):
    driver, stream = Mock(), io.StringIO()
    driver.create.side_effect = RuntimeError("sensitive provider diagnostic")
    driver.cleanup.return_value = False
    assert not measure(config(), driver, stream)
    row = json.loads(stream.getvalue())
    assert not row["cleanup_verified"] and row["terminate_ms"] is None
    assert "sensitive provider diagnostic" not in capsys.readouterr().err
    driver.cleanup.assert_called_once_with(None, row["run_id"])


def test_keyboard_interrupt_still_cleans_and_records():
    driver, stream = Mock(), io.StringIO()
    driver.probe.side_effect = KeyboardInterrupt
    driver.cleanup.return_value = True
    with pytest.raises(KeyboardInterrupt):
        measure(config(), driver, stream)
    row = json.loads(stream.getvalue())
    assert not row["completed"] and row["cleanup_verified"]


def test_e2b_private_network_and_lease_and_observed_deletion():
    sdk = Mock()
    sdk.SandboxNotFoundException = KeyError
    sandbox = sdk.Sandbox.create.return_value
    sandbox.sandbox_id = "owned"
    sandbox.get_info.return_value = SimpleNamespace(
        allow_internet_access=False,
        network={"allow_public_traffic": False},
        template_id="immutable",
        started_at=datetime.now(UTC),
        end_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    sandbox.commands.run.return_value = SimpleNamespace(exit_code=0, stdout="SB001_READY minimal\n")
    driver = E2BDriver(sdk)
    job = config("e2b")
    driver.create(job, "run")
    kwargs = sdk.Sandbox.create.call_args.kwargs
    assert kwargs["timeout"] == TTL_SECONDS
    assert (
        kwargs["allow_internet_access"] is False
        and kwargs["network"]["allow_public_traffic"] is False
    )
    assert kwargs["lifecycle"]["on_timeout"] == "kill" and kwargs["metadata"]["sb001_run"] == "run"
    driver.probe(sandbox, job)
    assert sandbox.commands.run.call_args.kwargs["user"] == "candidate"
    sdk.Sandbox.get_info.side_effect = KeyError
    assert driver.cleanup(sandbox, "run")
    sdk.Sandbox.kill.assert_called_once()
    sandbox.get_info.return_value.network["allow_public_traffic"] = True
    with pytest.raises(RuntimeError, match="network"):
        driver.probe(sandbox, job)
    assert sandbox.commands.run.call_count == 1


def test_daytona_private_network_and_lease_and_rejected_readiness():
    sdk = Mock()
    sdk.DaytonaNotFoundError = KeyError
    sdk.CreateSandboxFromSnapshotParams.side_effect = lambda **params: SimpleNamespace(
        model_dump=lambda: params
    )
    driver = DaytonaDriver(sdk)
    job = config()
    sandbox = driver.create(job, "run")
    params = driver.client.create.call_args.args[0].model_dump()
    assert params["ttl_minutes"] == 5 and params["network_block_all"] and not params["public"]
    assert params["os_user"] == "candidate" and params["labels"]["sb001_run"] == "run"
    now = datetime.now(UTC)
    sandbox.public, sandbox.network_block_all, sandbox.target = False, True, "us"
    sandbox.created_at, sandbox.auto_destroy_at = now, now + timedelta(minutes=5)
    sandbox.process.exec.return_value = SimpleNamespace(exit_code=0, result="incorrect")
    with pytest.raises(RuntimeError, match="marker"):
        driver.probe(sandbox, job)
    driver.client.get.side_effect = KeyError
    assert driver.cleanup(sandbox, "run")
    sandbox.delete.assert_called_once_with(timeout=30, wait=True)
    assert not driver.cleanup(None, "ambiguous")


def test_reject_unknown_workload_and_unpinned_images():
    fields = vars(config())
    for change in ({"image_digest": "latest"}, {"workload": "unregistered"}):
        with pytest.raises(ValueError):
            Workload(**(fields | change))


@pytest.mark.parametrize("provider", ["e2b", "daytona"])
def test_recovery_checks_ownership_before_deleting_known_resource(provider):
    sdk = Mock()
    if provider == "e2b":
        driver = E2BDriver(sdk)
        sdk.SandboxNotFoundException = KeyError
        sdk.Sandbox.get_info.return_value.metadata = {"sb001_run": "another"}
        delete = sdk.Sandbox.kill
    else:
        driver = DaytonaDriver(sdk)
        sdk.DaytonaNotFoundError = KeyError
        sandbox = driver.client.get.return_value
        sandbox.labels = {"sb001_run": "another"}
        delete = sandbox.delete
    assert not driver.recover("requested", "known")
    delete.assert_not_called()


def test_durable_run_journal_recovers_interrupted_result_once(tmp_path):
    from dataclasses import asdict
    from uuid import uuid4

    from benchmarks.sb001.run import reconcile

    run_id = str(uuid4())
    job = config()
    driver = Mock()
    driver.recover.return_value = True
    with (
        (tmp_path / "journal.jsonl").open("w+") as journal,
        (tmp_path / "rows.jsonl").open("a+") as output,
    ):
        journal.write(
            json.dumps({"event": "intent", "run_id": run_id, "config": asdict(job)}) + "\n"
        )
        journal.write(json.dumps({"event": "allocated", "sandbox_id": "owned"}) + "\n")
        assert reconcile(job, driver, output, journal, run_id)
        assert reconcile(job, driver, output, journal, run_id)
        driver.recover.assert_called_once_with(run_id, "owned")
        output.seek(0)
        (row,) = map(json.loads, output)
        assert row["run_id"] == run_id and not row["cleanup_verified"] and not row["completed"]
        assert row["ready_ms"] is None and row["terminate_ms"] is None


def test_intent_exists_before_creation_and_returned_identity_is_durable(tmp_path):
    job = config()
    journal_file = tmp_path / "journal.jsonl"
    driver = Mock()

    def create(_config, run_id, *, ttl_seconds):
        first = json.loads(journal_file.read_text().splitlines()[0])
        assert (
            first["run_id"] == run_id
            and first["event"] == "intent"
            and first["ttl_seconds"] == ttl_seconds
        )
        return SimpleNamespace(id="owned")

    driver.create.side_effect = create
    driver.cleanup.return_value = True
    with journal_file.open("x+") as journal:
        assert measure(job, driver, io.StringIO(), journal=journal)
    assert [entry["event"] for entry in map(json.loads, journal_file.read_text().splitlines())] == [
        "intent",
        "allocated",
        "outcome",
    ]


def test_extended_interactive_lease(tmp_path, monkeypatch):
    from benchmarks.sb001 import interactive

    job = Workload(**(vars(config()) | {"workload": "interactive"}))
    run = Mock()
    monkeypatch.setattr(interactive, "run_interactive", run)
    driver = Mock()
    driver.cleanup.return_value = True
    detail, rows = io.StringIO(), io.StringIO()
    assert measure(job, driver, rows, detail)
    assert (
        driver.create.call_args.kwargs["ttl_seconds"]
        == driver.probe.call_args.kwargs["ttl_seconds"]
        == 7200
    )
    assert run.call_args.args[-1] is detail


def test_reconcile_preserves_torn_suffixes_and_recovers_complete_intent(tmp_path):
    from dataclasses import asdict
    from uuid import uuid4

    from benchmarks.sb001.run import reconcile

    run_id, job, driver = str(uuid4()), config(), Mock()
    intent = {"event": "intent", "run_id": run_id, "config": asdict(job)}
    known = {"event": "allocated", "sandbox_id": "owned"}
    journal_path, rows_path = tmp_path / "journal", tmp_path / "rows"
    journal_path.write_text(json.dumps(intent) + "\n" + json.dumps(known) + '\n{"event":')
    rows_path.write_text('{"previous":')
    driver.recover.return_value = True
    with journal_path.open("r+") as journal, rows_path.open("a+") as rows:
        assert reconcile(job, driver, rows, journal, run_id)
        assert reconcile(job, driver, rows, journal, run_id)
    driver.recover.assert_called_once_with(run_id, "owned")
    assert {file.read_text() for file in tmp_path.glob("*.partial")} == {
        '{"previous":',
        '{"event":',
    }
    (row,) = rows_path.read_text().splitlines()
    assert json.loads(row)["terminate_ms"] is None


def test_cli_rejects_alias_to_input_before_loading_provider(tmp_path, monkeypatch):
    import os
    import sys
    from dataclasses import asdict

    from benchmarks.sb001 import run

    source, alias = tmp_path / "config", tmp_path / "alias"
    source.write_text(json.dumps(asdict(config())))
    os.link(source, alias)
    monkeypatch.setattr(sys, "argv", ["probe", str(source), "--measure", str(alias)])
    loader = Mock()
    monkeypatch.setattr(run, "load_driver", loader)
    with pytest.raises(SystemExit) as exit_info:
        run.main()
    assert exit_info.value.code == 2
    loader.assert_not_called()
