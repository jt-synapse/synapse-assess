"""Trusted integration boundary for managed execution. Candidate content stays opaque."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from synapse_contracts.models import (
    ExecutionRequest,
    ExecutionResult,
    FileContent,
    FileCreate,
    FileList,
    FileMutation,
    FileRename,
    FileRevision,
    FileWrite,
    Workspace,
)


class SandboxError(Exception):
    """Base error raised at the sandbox provider boundary."""


class SandboxNotFoundError(SandboxError):
    """The referenced sandbox handle does not exist or has been terminated."""


class RevisionConflictError(SandboxError):
    """Expected file or workspace revision does not match the authoritative sandbox state."""


class OperationConflictError(SandboxError):
    """An operation ID was reused with different parameters."""


class FileConflictError(SandboxError):
    """Target file already exists or is missing."""


class CommandNotFoundError(SandboxError):
    """Requested execution command ID is not approved for this sandbox."""


@dataclass(frozen=True)
class ResourceLimits:
    cpu_millicores: int
    memory_bytes: int
    storage_bytes: int
    processes: int
    command_timeout_seconds: int


@dataclass(frozen=True)
class SandboxSpec:
    session_id: UUID
    image_digest: str
    candidate_artifact_sha256: str
    services: tuple[Literal["postgresql"], ...]
    expires_at: datetime
    limits: ResourceLimits
    # Empty by default. Any permitted destinations must come from trusted configuration.
    allowed_egress: tuple[str, ...] = ()


@dataclass(frozen=True)
class SandboxHandle:
    sandbox_id: str
    session_id: UUID

    def __post_init__(self) -> None:
        if not self.sandbox_id.strip():
            raise ValueError("sandbox_id must be a nonempty provider identifier")


@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: UUID
    session_id: UUID
    kind: Literal["workspace", "database_consistent", "stage_source"]


class TerminalHandle(Protocol):
    async def read(self) -> bytes: ...
    async def write(self, data: bytes) -> None: ...
    async def resize(self, rows: int, cols: int) -> None: ...
    async def close(self) -> None: ...


class SandboxProvider(Protocol):
    async def provision(self, spec: SandboxSpec) -> SandboxHandle: ...
    async def health(self, handle: SandboxHandle) -> bool: ...
    async def list_files(self, handle: SandboxHandle) -> FileList: ...
    async def read_file(self, handle: SandboxHandle, path: str) -> FileContent: ...
    async def write_file(self, handle: SandboxHandle, file: FileWrite) -> FileRevision: ...
    async def create_file(self, handle: SandboxHandle, file: FileCreate) -> FileRevision: ...
    async def rename_file(self, handle: SandboxHandle, file: FileRename) -> FileRevision: ...
    async def delete_file(self, handle: SandboxHandle, file: FileMutation) -> Workspace: ...
    async def execute(
        self, handle: SandboxHandle, request: ExecutionRequest
    ) -> ExecutionResult: ...
    async def open_terminal(self, handle: SandboxHandle) -> TerminalHandle: ...
    async def snapshot(
        self,
        handle: SandboxHandle,
        kind: Literal["workspace", "database_consistent", "stage_source"],
    ) -> Checkpoint: ...
    async def restore(self, checkpoint: Checkpoint, spec: SandboxSpec) -> SandboxHandle: ...
    async def terminate(self, handle: SandboxHandle) -> None: ...
