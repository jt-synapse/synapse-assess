"""In-memory test fixture. This module is excluded from the installable provider package."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal
from uuid import UUID, uuid4

from synapse_contracts.models import (
    ExecutionRequest,
    ExecutionResult,
    FileContent,
    FileCreate,
    FileEntry,
    FileList,
    FileMutation,
    FileRename,
    FileRevision,
    FileWrite,
    Workspace,
)
from synapse_execution.provider import (
    Checkpoint,
    CommandNotFoundError,
    FileConflictError,
    OperationConflictError,
    RevisionConflictError,
    SandboxHandle,
    SandboxNotFoundError,
    SandboxSpec,
)


@dataclass
class Files:
    files: dict[str, FileContent]
    revision: int = 0
    operations: dict[UUID, tuple[Any, Any]] = field(default_factory=dict)


class FixtureTerminal:
    async def read(self) -> bytes:
        return b""

    async def write(self, data: bytes) -> None:
        pass

    async def resize(self, rows: int, cols: int) -> None:
        pass

    async def close(self) -> None:
        pass


class FixtureProvider:
    def __init__(self, files: list[FileContent], runs: dict[str, ExecutionResult]) -> None:
        self.initial = {file.path: file for file in files}
        self.runs = runs
        self.sandboxes: dict[SandboxHandle, Files] = {}
        self.checkpoints: dict[Checkpoint, Files] = {}

    def _state(self, handle: SandboxHandle) -> Files:
        if handle not in self.sandboxes:
            raise SandboxNotFoundError(handle.sandbox_id)
        return self.sandboxes[handle]

    def _replay(self, state: Files, operation_id: UUID, request: Any) -> Any | None:
        if operation_id not in state.operations:
            return None
        previous, result = state.operations[operation_id]
        if previous != request:
            raise OperationConflictError("operation ID reused with different input")
        return result

    async def provision(self, spec: SandboxSpec) -> SandboxHandle:
        handle = SandboxHandle(f"fixture-{uuid4().hex}", spec.session_id)
        self.sandboxes[handle] = Files(dict(self.initial))
        return handle

    async def health(self, handle: SandboxHandle) -> bool:
        return handle in self.sandboxes

    async def list_files(self, handle: SandboxHandle) -> FileList:
        state = self._state(handle)
        entries = [
            FileEntry(path=item.path, revision=item.revision)
            for item in sorted(state.files.values(), key=lambda f: f.path)
        ]
        return FileList(workspace_revision=state.revision, files=entries)

    async def read_file(self, handle: SandboxHandle, path: str) -> FileContent:
        state = self._state(handle)
        if path not in state.files:
            raise FileConflictError(f"file not found: {path}")
        return state.files[path]

    async def write_file(self, handle: SandboxHandle, file: FileWrite) -> FileRevision:
        state = self._state(handle)
        replayed: FileRevision | None = self._replay(state, file.client_operation_id, file)
        if replayed is not None:
            return replayed
        if file.path not in state.files:
            raise FileConflictError(f"file not found: {file.path}")
        current = state.files[file.path]
        if current.revision != file.expected_revision:
            raise RevisionConflictError("WORKSPACE_REVISION_CONFLICT")
        state.revision += 1
        updated = FileContent(path=file.path, revision=current.revision + 1, content=file.content)
        state.files[file.path] = updated
        result = FileRevision(
            path=file.path,
            revision=updated.revision,
            workspace_revision=state.revision,
            content_sha256=sha256(file.content.encode()).hexdigest(),
            saved_at=datetime.now(UTC),
        )
        state.operations[file.client_operation_id] = (file, result)
        return result

    async def create_file(self, handle: SandboxHandle, file: FileCreate) -> FileRevision:
        state = self._state(handle)
        replayed: FileRevision | None = self._replay(state, file.client_operation_id, file)
        if replayed is not None:
            return replayed
        if state.revision != file.expected_workspace_revision:
            raise RevisionConflictError("WORKSPACE_REVISION_CONFLICT")
        if file.path in state.files:
            raise FileConflictError(f"file already exists: {file.path}")
        state.revision += 1
        created = FileContent(path=file.path, revision=1, content=file.content)
        state.files[file.path] = created
        result = FileRevision(
            path=file.path,
            revision=created.revision,
            workspace_revision=state.revision,
            content_sha256=sha256(file.content.encode()).hexdigest(),
            saved_at=datetime.now(UTC),
        )
        state.operations[file.client_operation_id] = (file, result)
        return result

    async def rename_file(self, handle: SandboxHandle, file: FileRename) -> FileRevision:
        state = self._state(handle)
        replayed: FileRevision | None = self._replay(state, file.client_operation_id, file)
        if replayed is not None:
            return replayed
        if file.path not in state.files:
            raise FileConflictError(f"file not found: {file.path}")
        if file.destination in state.files:
            raise FileConflictError(f"destination already exists: {file.destination}")
        current = state.files[file.path]
        if current.revision != file.expected_revision:
            raise RevisionConflictError("WORKSPACE_REVISION_CONFLICT")
        state.revision += 1
        del state.files[file.path]
        moved = FileContent(
            path=file.destination, revision=current.revision + 1, content=current.content
        )
        state.files[file.destination] = moved
        result = FileRevision(
            path=file.destination,
            revision=moved.revision,
            workspace_revision=state.revision,
            content_sha256=sha256(moved.content.encode()).hexdigest(),
            saved_at=datetime.now(UTC),
        )
        state.operations[file.client_operation_id] = (file, result)
        return result

    async def delete_file(self, handle: SandboxHandle, file: FileMutation) -> Workspace:
        state = self._state(handle)
        replayed: Workspace | None = self._replay(state, file.client_operation_id, file)
        if replayed is not None:
            return replayed
        if file.path not in state.files:
            raise FileConflictError(f"file not found: {file.path}")
        current = state.files[file.path]
        if current.revision != file.expected_revision:
            raise RevisionConflictError("WORKSPACE_REVISION_CONFLICT")
        state.revision += 1
        del state.files[file.path]
        result = Workspace(status="READY", revision=state.revision)
        state.operations[file.client_operation_id] = (file, result)
        return result

    async def execute(self, handle: SandboxHandle, request: ExecutionRequest) -> ExecutionResult:
        state = self._state(handle)
        if request.command_id not in self.runs:
            raise CommandNotFoundError(request.command_id)
        result = self.runs[request.command_id]
        if (
            request.workspace_revision != state.revision
            or result.workspace_revision != state.revision
        ):
            raise RevisionConflictError("WORKSPACE_REVISION_CONFLICT")
        return result

    async def open_terminal(self, handle: SandboxHandle) -> FixtureTerminal:
        self._state(handle)
        return FixtureTerminal()

    async def snapshot(
        self,
        handle: SandboxHandle,
        kind: Literal["workspace", "database_consistent", "stage_source"],
    ) -> Checkpoint:
        if kind == "database_consistent":
            raise NotImplementedError("an in-memory fixture cannot produce database checkpoints")
        state = self._state(handle)
        ref = Checkpoint(uuid4(), handle.session_id, kind)
        self.checkpoints[ref] = Files(dict(state.files), state.revision)
        return ref

    async def restore(self, checkpoint: Checkpoint, spec: SandboxSpec) -> SandboxHandle:
        if checkpoint.session_id != spec.session_id or checkpoint.kind != "workspace":
            raise ValueError("restore requires a workspace checkpoint owned by this session")
        state = self.checkpoints[checkpoint]
        handle = await self.provision(spec)
        self.sandboxes[handle] = Files(dict(state.files), state.revision)
        return handle

    async def terminate(self, handle: SandboxHandle) -> None:
        self.sandboxes.pop(handle, None)
