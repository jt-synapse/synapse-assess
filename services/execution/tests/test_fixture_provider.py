import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from synapse_contracts.models import (
    ExecutionRequest,
    ExecutionResult,
    FileContent,
    FileCreate,
    FileMutation,
    FileRename,
    FileWrite,
)
from synapse_execution import (
    CommandNotFoundError,
    FileConflictError,
    OperationConflictError,
    ResourceLimits,
    RevisionConflictError,
    SandboxHandle,
    SandboxNotFoundError,
    SandboxProvider,
    SandboxSpec,
)

from .support.fixture_provider import FixtureProvider


def test_contract_fixture_lifecycle():
    async def lifecycle():
        session_id = uuid4()
        spec = SandboxSpec(
            session_id,
            "sha256:" + "0" * 64,
            "1" * 64,
            (),
            datetime.now(UTC),
            ResourceLimits(500, 256_000_000, 10_000_000, 10, 30),
        )
        first = FileContent(path="demo.txt", revision=0, content="one")
        execution = ExecutionResult(
            execution_id=uuid4(),
            workspace_revision=4,
            command=["fixture"],
            status="COMPLETED",
            exit_code=0,
            duration_ms=1,
            stdout_artifact_id=uuid4(),
            stderr_artifact_id=uuid4(),
        )
        adapter: SandboxProvider = FixtureProvider([first], {"visible": execution})
        handle = await adapter.provision(spec)
        assert isinstance(handle.sandbox_id, str) and handle.sandbox_id
        assert handle.session_id == spec.session_id
        assert await adapter.health(handle)

        save = FileWrite(
            path=first.path, content="two", client_operation_id=uuid4(), expected_revision=0
        )
        revision = await adapter.write_file(handle, save)
        assert await adapter.write_file(handle, save) == revision
        with pytest.raises(OperationConflictError):
            await adapter.write_file(handle, save.model_copy(update={"content": "different"}))
        with pytest.raises(RevisionConflictError, match="WORKSPACE_REVISION_CONFLICT"):
            await adapter.write_file(
                handle, save.model_copy(update={"client_operation_id": uuid4()})
            )

        created = await adapter.create_file(
            handle,
            FileCreate(
                path="extra.py",
                content="print('ok')\n",
                expected_workspace_revision=1,
                client_operation_id=uuid4(),
            ),
        )
        assert created.workspace_revision == 2
        with pytest.raises(FileConflictError):
            await adapter.create_file(
                handle,
                FileCreate(
                    path="extra.py",
                    content="dup",
                    expected_workspace_revision=2,
                    client_operation_id=uuid4(),
                ),
            )
        renamed = await adapter.rename_file(
            handle,
            FileRename(
                path="extra.py",
                destination="renamed.py",
                expected_revision=1,
                client_operation_id=uuid4(),
            ),
        )
        assert renamed.path == "renamed.py" and renamed.workspace_revision == 3
        listing = await adapter.list_files(handle)
        assert [entry.path for entry in listing.files] == ["demo.txt", "renamed.py"]
        deleted = await adapter.delete_file(
            handle,
            FileMutation(
                path="renamed.py",
                expected_revision=renamed.revision,
                client_operation_id=uuid4(),
            ),
        )
        assert deleted.revision == 4

        req = ExecutionRequest(
            client_operation_id=uuid4(), workspace_revision=4, command_id="visible"
        )
        assert await adapter.execute(handle, req) == execution
        with pytest.raises(CommandNotFoundError):
            await adapter.execute(handle, req.model_copy(update={"command_id": "unknown"}))
        with pytest.raises(RevisionConflictError):
            await adapter.execute(handle, req.model_copy(update={"workspace_revision": 0}))

        terminal = await adapter.open_terminal(handle)
        await terminal.write(b"example")
        assert await terminal.read() == b""
        await terminal.close()

        checkpoint = await adapter.snapshot(handle, "workspace")
        with pytest.raises(NotImplementedError):
            await adapter.snapshot(handle, "database_consistent")
        await adapter.terminate(handle)
        await adapter.terminate(handle)
        assert not await adapter.health(handle)
        with pytest.raises(SandboxNotFoundError):
            await adapter.list_files(handle)
        with pytest.raises(ValueError):
            await adapter.restore(checkpoint, replace(spec, session_id=uuid4()))
        restored = await adapter.restore(checkpoint, spec)
        assert (await adapter.read_file(restored, first.path)).content == "two"

        with pytest.raises(ValueError, match="nonempty"):
            SandboxHandle("   ", session_id)

    asyncio.run(lifecycle())
