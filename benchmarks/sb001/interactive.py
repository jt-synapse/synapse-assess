"""Provider-side PTY and longevity scenario for an explicitly requested SB-001 run."""

from __future__ import annotations

import json
import shlex
import signal
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from importlib import import_module
from threading import current_thread, main_thread
from typing import Any, Protocol, TextIO
from uuid import UUID

DURATION_SECONDS = 110 * 60
HEARTBEAT_SECONDS = 60
IO_TIMEOUT = 20
FRAME = b"\x1eSB001:"
PAYLOAD = bytes(range(256)) * 256

# The fixed helper changes its own PTY to raw mode. A single byte echoes immediately,
# independent of shell line editing. Its random token lives only in this process.
_HELPER = r"""
import os, sys, tty
tty.setraw(0)
token = os.urandom(16).hex().encode()
def send(data):
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()
def identity():
    send(b'\x1eSB001:' + token + b'\x1f')
identity()
while True:
    key = os.read(0, 1)
    if not key or key == b'Q': break
    if key == b'I': identity()
    elif key == b'B': send(bytes(range(256)) * 256 + b'\x1eEND\x1f')
    else: send(key)
"""
_BOOT = ("exec python3 -I -u -c " + shlex.quote(_HELPER) + "\r").encode()


class Terminal(Protocol):
    def check_owner(self) -> None: ...
    def open(self) -> Iterator[bytes]: ...
    def write(self, data: bytes) -> None: ...
    def detach(self) -> None: ...
    def reconnect(self) -> Iterator[bytes]: ...
    def terminate(self) -> None: ...


class E2BTerminal:
    def __init__(self, sandbox: Any, run_id: str) -> None:
        self.sandbox = sandbox
        self.run_id = run_id
        self.pid: int | None = None
        self.handle: Any = None

    def check_owner(self) -> None:
        info = self.sandbox.get_info(request_timeout=IO_TIMEOUT)
        if (info.metadata or {}).get("sb001_run") != self.run_id:
            raise ValueError("unexpected sandbox owner")

    def open(self) -> Iterator[bytes]:
        size = import_module("e2b").PtySize(rows=30, cols=120)
        self.handle = self.sandbox.pty.create(
            size=size, user="candidate", timeout=DURATION_SECONDS + 240
        )
        self.pid = self.handle.pid
        return (data for _, _, data in self.handle if data is not None)

    def write(self, data: bytes) -> None:
        self.sandbox.pty.send_stdin(self.pid, data, request_timeout=IO_TIMEOUT)

    def detach(self) -> None:
        if self.handle is not None:
            self.handle.disconnect()
            self.handle = None

    def reconnect(self) -> Iterator[bytes]:
        self.handle = self.sandbox.pty.connect(self.pid, timeout=DURATION_SECONDS + 240)
        return (data for _, _, data in self.handle if data is not None)

    def terminate(self) -> None:
        if self.pid is not None:
            self.sandbox.pty.kill(self.pid, request_timeout=IO_TIMEOUT)


class DaytonaTerminal:
    def __init__(self, sandbox: Any, run_id: str) -> None:
        self.sandbox = sandbox
        self.run_id = run_id
        self.session = "sb001-" + run_id
        self.handle: Any = None

    def check_owner(self) -> None:
        self.sandbox.refresh_data(request_timeout=IO_TIMEOUT)
        if (self.sandbox.labels or {}).get(
            "sb001_run"
        ) != self.run_id or self.sandbox.user != "candidate":
            raise ValueError("unexpected sandbox owner or user")

    def open(self) -> Iterator[bytes]:
        self.handle = self.sandbox.process.create_pty_session(id=self.session)
        return iter(self.handle)

    def write(self, data: bytes) -> None:
        self.handle.send_input(data)

    def detach(self) -> None:
        if self.handle is not None:
            self.handle.disconnect()
            self.handle = None

    def reconnect(self) -> Iterator[bytes]:
        self.handle = self.sandbox.process.connect_pty_session(session_id=self.session)
        return iter(self.handle)

    def terminate(self) -> None:
        self.sandbox.process.kill_pty_session(self.session, request_timeout=IO_TIMEOUT)


class _Deadline(BaseException):
    """Escape even an SDK's generic exception retry handler."""


@contextmanager
def _bounded_io() -> Iterator[None]:
    # Daytona's synchronous PTY iterator has no per-read timeout. Bound the entire
    # operation, including partial frames and reconnect handshakes, in the CLI thread.
    if current_thread() is not main_thread() or not hasattr(signal, "setitimer"):
        raise RuntimeError("interactive measurement requires a POSIX main thread")
    if signal.getitimer(signal.ITIMER_REAL)[0]:
        raise RuntimeError("another realtime deadline is active")

    def expire(*_: object) -> None:
        raise _Deadline

    old_handler = signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, IO_TIMEOUT)
    try:
        yield
    except _Deadline:
        raise TimeoutError("PTY operation timed out") from None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)


class Reader:
    def __init__(self, chunks: Iterator[bytes]) -> None:
        self.chunks = chunks
        self.buffer = bytearray()

    def read(self, count: int) -> bytes:
        while len(self.buffer) < count:
            self._receive()
        result = bytes(self.buffer[:count])
        del self.buffer[:count]
        return result

    def _receive(self) -> None:
        chunk = next(self.chunks, None)
        if chunk is None:
            raise EOFError("PTY disconnected")
        if len(self.buffer) + len(chunk) > 2 * len(PAYLOAD):
            raise ValueError("unexpected PTY output volume")
        self.buffer.extend(chunk)

    def identity(self, *, initial: bool = False) -> bytes:
        if initial:
            # The login prompt and shell echo precede the first binary frame.
            while FRAME not in self.buffer:
                self._receive()
            del self.buffer[: self.buffer.index(FRAME)]
        if self.read(len(FRAME)) != FRAME:
            raise ValueError("unexpected identity frame")
        token = self.read(32)
        if self.read(1) != b"\x1f" or any(c not in b"0123456789abcdef" for c in token):
            raise ValueError("malformed process identity")
        return token


@dataclass
class Measurements:
    run_id: str
    provider: str
    connect_to_ready_ms: float | None = None
    reconnect_to_same_pty_ms: float | None = None
    controlled_output_verified: bool = False
    verified_payload_bytes: int = 0
    keystroke_echo_ms: list[float] = field(default_factory=list)
    heartbeat_count: int = 0
    observed_seconds: float = 0.0
    stage_revocation_ms: None = None
    completed: bool = False
    error: str | None = None


def _exercise(
    terminal: Terminal,
    result: Measurements,
    now: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    with _bounded_io():
        terminal.check_owner()
    try:
        with _bounded_io():
            opening = now()
            reader = Reader(terminal.open())
            terminal.write(_BOOT)
            identity = reader.identity(initial=True)
            result.connect_to_ready_ms = (now() - opening) * 1000
        with _bounded_io():
            terminal.write(b"B")
            if reader.read(len(PAYLOAD)) != PAYLOAD or reader.read(5) != b"\x1eEND\x1f":
                raise ValueError("controlled output mismatch")
            result.controlled_output_verified = True
            result.verified_payload_bytes = len(PAYLOAD)
            terminal.detach()
        with _bounded_io():
            reconnecting = now()
            reader = Reader(terminal.reconnect())
            terminal.write(b"I")
            if reader.identity() != identity:
                raise ValueError("PTY did not reconnect to the original process")
            result.reconnect_to_same_pty_ms = (now() - reconnecting) * 1000

        start = now()
        for offset in range(0, DURATION_SECONDS + 1, HEARTBEAT_SECONDS):
            due = start + offset
            sleep(max(0, due - now()))
            if now() > due + IO_TIMEOUT:
                raise TimeoutError("missed scheduled longevity observation")
            with _bounded_io():
                # Each raw keystroke must return exactly once in sequence.
                key = bytes([ord("a") + result.heartbeat_count % 26])
                sent = now()
                terminal.write(key)
                if reader.read(1) != key:
                    raise ValueError("keystroke echo mismatch")
                received = now()
                result.keystroke_echo_ms.append((received - sent) * 1000)
                result.heartbeat_count += 1
                result.observed_seconds = received - start
    finally:
        try:
            with _bounded_io():
                terminal.detach()
        finally:
            with _bounded_io():
                terminal.terminate()


def run_interactive(sandbox: Any, provider: str, run_id: str, detail: TextIO) -> None:
    """Operate only on the run-owned sandbox, append one result, and propagate failures."""
    UUID(run_id)
    if provider not in {"e2b", "daytona"}:
        raise ValueError("unsupported benchmark provider")
    terminal = (
        E2BTerminal(sandbox, run_id) if provider == "e2b" else DaytonaTerminal(sandbox, run_id)
    )
    result = Measurements(run_id, provider)
    try:
        _exercise(terminal, result)
        result.completed = True
    except BaseException as exc:
        result.error = type(exc).__name__
        raise
    finally:
        detail.write(json.dumps(asdict(result)) + "\n")
        detail.flush()
