import io
import json
from collections import deque
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from benchmarks.sb001 import interactive as task


class Clock:
    seconds = 0.0

    def now(self):
        return self.seconds

    def sleep(self, period):
        self.seconds += period


class FixtureTerminal:
    def __init__(self, clock, *, corrupt=False, reconnect_identity=None):
        self.clock = clock
        self.chunks = deque()
        self.token = b"0" * 32
        self.reconnect_identity = reconnect_identity
        self.corrupt = corrupt
        self.terminated = False
        self.detaches = 0

    def check_owner(self):
        pass

    def _stream(self):
        while self.chunks:
            yield self.chunks.popleft()

    def open(self):
        return self._stream()

    def reconnect(self):
        return self._stream()

    def write(self, data):
        self.clock.seconds += 0.01
        if data == task._BOOT:
            self.chunks.extend([b"$ " + data, task.FRAME[:2], task.FRAME[2:], self.token, b"\x1f"])
        elif data == b"B":
            output = task.PAYLOAD if not self.corrupt else task.PAYLOAD[:-1] + b"X"
            self.chunks.extend([output[:2048], output[2048:] + b"\x1eEND\x1f"])
        elif data == b"I":
            self.chunks.append(task.FRAME + (self.reconnect_identity or self.token) + b"\x1f")
        else:
            self.chunks.append(data)

    def detach(self):
        self.detaches += 1

    def terminate(self):
        self.terminated = True


def test_full_synthetic_session_survives_reconnect_and_110_minutes_of_observations():
    clock = Clock()
    terminal = FixtureTerminal(clock)
    record = task.Measurements(str(uuid4()), "daytona")
    task._exercise(terminal, record, clock.now, clock.sleep)
    assert record.connect_to_ready_ms == pytest.approx(10)
    assert record.reconnect_to_same_pty_ms == pytest.approx(10)
    assert record.keystroke_echo_ms == pytest.approx([10] * 111)
    assert record.heartbeat_count == 111 and record.observed_seconds >= 6600
    assert record.controlled_output_verified and record.verified_payload_bytes == 65536
    assert record.stage_revocation_ms is None
    assert terminal.detaches == 2 and terminal.terminated


@pytest.mark.parametrize("kwargs", [{"corrupt": True}, {"reconnect_identity": b"1" * 32}])
def test_corrupt_output_or_changed_process_fails_and_closes_terminal(kwargs):
    clock = Clock()
    terminal = FixtureTerminal(clock, **kwargs)
    with pytest.raises(ValueError):
        task._exercise(terminal, task.Measurements(str(uuid4()), "e2b"), clock.now, clock.sleep)
    assert terminal.terminated


def test_controller_sleep_cannot_be_reported_as_continuous_activity():
    clock = Clock()
    terminal = FixtureTerminal(clock)
    record = task.Measurements(str(uuid4()), "daytona")
    with pytest.raises(TimeoutError, match="missed scheduled"):
        task._exercise(terminal, record, clock.now, lambda seconds: clock.sleep(seconds + 90))
    assert terminal.terminated and record.heartbeat_count == 0


@pytest.mark.parametrize("provider", ["e2b", "daytona"])
def test_mismatched_owner_cannot_operate_or_destroy_a_terminal(provider):
    sandbox = Mock(labels={"sb001_run": "other"}, user="candidate")
    sandbox.get_info.return_value.metadata = {"sb001_run": "other"}
    run_id = str(uuid4())
    out = io.StringIO()
    with pytest.raises(ValueError):
        task.run_interactive(sandbox, provider, run_id, out)
    record = json.loads(out.getvalue())
    assert record["run_id"] == run_id and record["error"] == "ValueError"
    assert not record["completed"]
    assert not sandbox.pty.method_calls and not sandbox.process.method_calls


def test_pinned_sdk_pty_methods_use_only_run_owned_identifiers(monkeypatch):
    run_id = str(uuid4())
    sandbox = Mock(user="candidate", labels={"sb001_run": run_id})
    sandbox.get_info.return_value.metadata = {"sb001_run": run_id}
    monkeypatch.setattr(task, "import_module", lambda _: SimpleNamespace(PtySize=Mock()))
    e2b_handle = Mock(pid=81)
    e2b_handle.__iter__ = Mock(return_value=iter([(None, None, b"data")]))
    sandbox.pty.create.return_value = e2b_handle
    sandbox.pty.connect.return_value = e2b_handle
    e2b = task.E2BTerminal(sandbox, run_id)
    e2b.check_owner()
    assert list(e2b.open()) == [b"data"]
    e2b.write(b"I")
    e2b.detach()
    e2b.reconnect()
    e2b.terminate()
    assert sandbox.pty.create.call_args.kwargs["user"] == "candidate"
    sandbox.pty.send_stdin.assert_called_once_with(81, b"I", request_timeout=task.IO_TIMEOUT)
    sandbox.pty.kill.assert_called_once_with(81, request_timeout=task.IO_TIMEOUT)

    daytona = task.DaytonaTerminal(sandbox, run_id)
    daytona.check_owner()
    handle = Mock()
    handle.__iter__ = Mock(return_value=iter([b"data"]))
    sandbox.process.create_pty_session.return_value = handle
    sandbox.process.connect_pty_session.return_value = handle
    assert list(daytona.open()) == [b"data"]
    daytona.write(b"I")
    daytona.detach()
    daytona.reconnect()
    daytona.terminate()
    sandbox.process.create_pty_session.assert_called_once_with(id=f"sb001-{run_id}")
    sandbox.process.connect_pty_session.assert_called_once_with(session_id=f"sb001-{run_id}")
    sandbox.process.kill_pty_session.assert_called_once_with(
        f"sb001-{run_id}", request_timeout=task.IO_TIMEOUT
    )


def test_real_benchmark_helper_echoes_one_raw_byte_and_exact_fixture_output():
    import os
    import pty
    import select
    import subprocess
    import sys

    try:
        master, slave = pty.openpty()
    except OSError as exc:
        pytest.skip(f"local PTY unavailable: {exc}")
    try:
        with subprocess.Popen(
            [sys.executable, "-I", "-u", "-c", task._HELPER],
            stdin=slave,
            stdout=slave,
            stderr=slave,
        ) as helper:
            try:

                def chunks():
                    while select.select([master], [], [], 2)[0]:
                        yield os.read(master, 4096)

                reader = task.Reader(chunks())
                token = reader.identity()
                os.write(master, b"aBI")
                assert reader.read(1) == b"a"
                assert reader.read(len(task.PAYLOAD)) == task.PAYLOAD
                assert reader.read(5) == b"\x1eEND\x1f"
                assert reader.identity() == token
                os.write(master, b"Q")
                assert helper.wait(timeout=2) == 0
            finally:
                if helper.poll() is None:
                    helper.kill()
    finally:
        os.close(slave)
        os.close(master)
