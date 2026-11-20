"""SDK boundary for the synthetic readiness benchmark. Imports are lazy for offline CI."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
from importlib.metadata import version
from typing import Any, Protocol

PINS = {"e2b": "2.64.0", "daytona": "0.232.0"}
TTL_SECONDS = 300
REQUEST_SECONDS = 30


@dataclass(frozen=True)
class Workload:
    provider: str
    template: str
    region: str
    profile: str
    workload: str
    image_digest: str
    start_kind: str

    def __post_init__(self) -> None:
        if self.provider not in PINS or self.workload not in {
            "minimal",
            "orderflow",
            "interactive",
        }:
            raise ValueError("unknown benchmark provider or workload")
        if self.start_kind not in {"cold", "warm"} or self.profile not in {"standard", "stress"}:
            raise ValueError("unknown start kind or profile")
        if not self.template.strip() or not self.region.strip():
            raise ValueError("specify a prebuilt template and region")
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", self.image_digest):
            raise ValueError("image digest must be sha256:<64 lowercase hex digits>")


class Driver(Protocol):
    def create(self, config: Workload, run_id: str, *, ttl_seconds: int = TTL_SECONDS) -> Any: ...
    def probe(self, sandbox: Any, config: Workload, *, ttl_seconds: int = TTL_SECONDS) -> None: ...
    def cleanup(self, sandbox: Any | None, run_id: str) -> bool: ...
    def recover(self, run_id: str, known_id: str | None) -> bool: ...


def _expect_ready(code: int, output: str, workload: str) -> None:
    if code != 0 or output.strip() != f"SB001_READY {workload}":
        raise RuntimeError("workload did not return its readiness marker")


class E2BDriver:
    def __init__(self, sdk: Any) -> None:
        self.sdk = sdk

    def create(self, config: Workload, run_id: str, *, ttl_seconds: int = TTL_SECONDS) -> Any:
        return self.sdk.Sandbox.create(
            template=config.template,
            timeout=ttl_seconds,
            request_timeout=REQUEST_SECONDS,
            metadata={"sb001_run": run_id},
            idempotency_key=run_id,
            allow_internet_access=False,
            network={"allow_public_traffic": False},
            lifecycle={"on_timeout": "kill"},
            debug=False,
        )

    def probe(self, sandbox: Any, config: Workload, *, ttl_seconds: int = TTL_SECONDS) -> None:
        info = sandbox.get_info(request_timeout=REQUEST_SECONDS)
        if (
            info.allow_internet_access is not False
            or (info.network or {}).get("allow_public_traffic") is not False
        ):
            raise RuntimeError("provider did not confirm private networking")
        if (
            info.template_id != config.template
            or (info.end_at - info.started_at).total_seconds() > ttl_seconds + 5
        ):
            raise RuntimeError("unexpected template or expiry")
        result = sandbox.commands.run(
            f"/opt/sb001/ready {config.workload}",
            user="candidate",
            timeout=REQUEST_SECONDS,
            request_timeout=REQUEST_SECONDS,
        )
        _expect_ready(result.exit_code, result.stdout, config.workload)

    def cleanup(self, sandbox: Any | None, run_id: str) -> bool:
        if sandbox is None:
            return self.recover(run_id, None)
        return self._terminate([sandbox.sandbox_id])

    def recover(self, run_id: str, known_id: str | None) -> bool:
        if known_id is not None:
            try:
                info = self.sdk.Sandbox.get_info(known_id, request_timeout=REQUEST_SECONDS)
            except self.sdk.SandboxNotFoundException:
                return True
            return info.metadata.get("sb001_run") == run_id and self._terminate([known_id])
        pages = self.sdk.Sandbox.list(
            query=self.sdk.SandboxQuery(metadata={"sb001_run": run_id}),
            request_timeout=REQUEST_SECONDS,
        )
        ids = []
        while pages.has_next:
            ids.extend(
                item.sandbox_id
                for item in pages.next_items(request_timeout=REQUEST_SECONDS)
                if item.metadata.get("sb001_run") == run_id
            )
        return bool(ids) and self._terminate(ids)

    def _terminate(self, ids: list[str]) -> bool:
        for sandbox_id in ids:
            self.sdk.Sandbox.kill(sandbox_id, request_timeout=REQUEST_SECONDS)
        deadline = time.monotonic() + REQUEST_SECONDS
        for sandbox_id in ids:
            while True:
                try:
                    self.sdk.Sandbox.get_info(sandbox_id, request_timeout=5)
                except self.sdk.SandboxNotFoundException:
                    break
                if time.monotonic() >= deadline:
                    return False
                time.sleep(0.25)
        return True


class DaytonaDriver:
    def __init__(self, sdk: Any) -> None:
        self.sdk = sdk
        self.client = sdk.Daytona()

    def create(self, config: Workload, run_id: str, *, ttl_seconds: int = TTL_SECONDS) -> Any:
        params = self.sdk.CreateSandboxFromSnapshotParams(
            name=f"sb001-{run_id}",
            labels={"sb001_run": run_id},
            snapshot=config.template,
            target=config.region,
            os_user="candidate",
            public=False,
            network_block_all=True,
            ttl_minutes=ttl_seconds // 60,
            auto_delete_interval=0,
        )
        # Older SDK models may silently ignore unknown kwargs. Check the serialized policy.
        policy = params.model_dump()
        if (
            policy.get("network_block_all") is not True
            or policy.get("ttl_minutes") != ttl_seconds // 60
        ):
            raise RuntimeError("SDK cannot express mandatory network and expiry settings")
        return self.client.create(params, timeout=REQUEST_SECONDS)

    def probe(self, sandbox: Any, config: Workload, *, ttl_seconds: int = TTL_SECONDS) -> None:
        sandbox.refresh_data(request_timeout=REQUEST_SECONDS)
        if (
            sandbox.public is not False
            or sandbox.network_block_all is not True
            or not sandbox.auto_destroy_at
        ):
            raise RuntimeError("provider did not confirm private networking and expiry")
        created = datetime.fromisoformat(str(sandbox.created_at))
        expires = datetime.fromisoformat(str(sandbox.auto_destroy_at))
        if not 0 < (expires - created).total_seconds() <= ttl_seconds + 5:
            raise RuntimeError("provider did not confirm bounded wall-clock expiry")
        if sandbox.target != config.region:
            raise RuntimeError("unexpected region")
        result = sandbox.process.exec(
            f"/opt/sb001/ready {config.workload}", timeout=REQUEST_SECONDS
        )
        _expect_ready(result.exit_code, result.result, config.workload)

    def cleanup(self, sandbox: Any | None, run_id: str) -> bool:
        if sandbox is None:
            return self.recover(run_id, None)
        sandbox.delete(timeout=REQUEST_SECONDS, wait=True)
        # API may retain a tombstone after reaching the documented destroyed state.
        try:
            observed = self.client.get(sandbox.id, request_timeout=REQUEST_SECONDS)
        except self.sdk.DaytonaNotFoundError:
            return True
        return observed.state == "destroyed"

    def recover(self, run_id: str, known_id: str | None) -> bool:
        try:
            sandbox = self.client.get(
                known_id or f"sb001-{run_id}", request_timeout=REQUEST_SECONDS
            )
        except self.sdk.DaytonaNotFoundError:
            return known_id is not None
        if (sandbox.labels or {}).get("sb001_run") != run_id:
            return False
        return sandbox.state == "destroyed" or self.cleanup(sandbox, run_id)


def load_driver(name: str) -> Driver:
    if version(name) != PINS[name]:
        raise RuntimeError(f"{name} SDK must be version {PINS[name]}")
    sdk = import_module(name)
    return E2BDriver(sdk) if name == "e2b" else DaytonaDriver(sdk)
