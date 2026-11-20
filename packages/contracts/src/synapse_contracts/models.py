"""Version 1 wire contracts. Server-derived fields are absent from mutation requests."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveInt,
    model_validator,
)


def _relative_path(value: str) -> str:
    if (
        not value
        or "\\" in value
        or any(not char.isprintable() for char in value)
        or re.match(r"^[A-Za-z]:", value)
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ValueError("use a normalized, relative POSIX path")
    return value


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


RelativePath = Annotated[str, Field(max_length=4096), AfterValidator(_relative_path)]
UtcTime = Annotated[AwareDatetime, AfterValidator(_utc)]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
ImageDigest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
StageId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")]
Text = Annotated[str, Field(min_length=1)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Liveness(Contract):
    status: Literal["alive"]


class Readiness(Contract):
    status: Literal["ready"]


class ErrorDetail(Contract):
    code: Text
    message: Text
    request_id: UUID


class ErrorEnvelope(Contract):
    error: ErrorDetail


class ArtifactSpec(Contract):
    path: RelativePath
    sha256: Sha256 | None


class RuntimeSpec(Contract):
    image: Text
    image_digest: ImageDigest | None


class StagePolicy(Contract):
    stage_id: StageId
    kind: Literal["independent", "assisted", "defense"]
    duration_minutes: PositiveInt
    instructions_path: RelativePath | None = None
    instructions_sha256: Sha256 | None = None
    ai_enabled: bool

    @model_validator(mode="after")
    def validate_ai_policy(self) -> Self:
        if self.instructions_sha256 and self.instructions_path is None:
            raise ValueError("instruction digest requires an instructions path")
        if self.ai_enabled and self.kind != "assisted":
            raise ValueError("AI access requires an assisted stage")
        return self


class AssessmentManifest(Contract):
    """Trusted package metadata. Drafts can identify artifacts pending publication."""

    schema_version: Literal[1]
    package_id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]*$")]
    version: Text
    title: Text
    runtime: RuntimeSpec
    services: list[Literal["postgresql"]]
    stages: Annotated[list[StagePolicy], Field(min_length=1)]
    candidate_artifact: ArtifactSpec
    evaluator_artifact: ArtifactSpec

    @model_validator(mode="after")
    def check_package(self) -> Self:
        if len(self.services) != len(set(self.services)):
            raise ValueError("duplicate service")
        if len({stage.stage_id for stage in self.stages}) != len(self.stages):
            raise ValueError("stage IDs must be unique")
        candidate = PurePosixPath(self.candidate_artifact.path)
        evaluator = PurePosixPath(self.evaluator_artifact.path)
        if candidate.is_relative_to(evaluator) or evaluator.is_relative_to(candidate):
            raise ValueError("candidate and evaluator artifacts must occupy disjoint paths")
        for stage in self.stages:
            if stage.instructions_path and PurePosixPath(stage.instructions_path).is_relative_to(
                evaluator
            ):
                raise ValueError("stage instructions cannot reference evaluator materials")
        return self

    def require_published(self) -> Self:
        if not all(
            (
                self.runtime.image_digest,
                self.candidate_artifact.sha256,
                self.evaluator_artifact.sha256,
            )
        ):
            raise ValueError("publication requires image and artifact digests")
        if any(stage.instructions_path and not stage.instructions_sha256 for stage in self.stages):
            raise ValueError("publication requires a digest for each stage brief")
        return self


class SessionState(StrEnum):
    CREATED = "CREATED"
    PROVISIONING = "PROVISIONING"
    READY = "READY"
    STAGE_A_ACTIVE = "STAGE_A_ACTIVE"
    STAGE_A_SEALING = "STAGE_A_SEALING"
    STAGE_B_ACTIVE = "STAGE_B_ACTIVE"
    STAGE_B_SEALING = "STAGE_B_SEALING"
    DEFENSE_ACTIVE = "DEFENSE_ACTIVE"
    SUBMITTED = "SUBMITTED"
    EVALUATING = "EVALUATING"
    REVIEWED = "REVIEWED"
    FINALIZED = "FINALIZED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class InviteRequest(Contract):
    candidate_id: UUID


class Invitation(Contract):
    invitation_id: UUID
    expires_at: UtcTime


class CreateSession(Contract):
    invitation_id: UUID


class ActiveStage(Contract):
    stage_id: StageId
    stage_attempt_id: UUID
    started_at: UtcTime
    deadline_at: UtcTime
    ai_enabled: bool


class Workspace(Contract):
    status: Literal["PENDING", "READY", "UNAVAILABLE", "CLOSED"]
    revision: NonNegativeInt


class Session(Contract):
    session_id: UUID
    assessment_version_id: UUID
    state: SessionState
    server_time: UtcTime
    stage: ActiveStage | None
    workspace: Workspace


class StageCompletion(Contract):
    stage_attempt_id: UUID
    expected_workspace_revision: NonNegativeInt


class WrittenReasoning(Contract):
    client_operation_id: UUID
    text: Text


class DefenseAnswer(WrittenReasoning):
    question_id: Text


class FileEntry(Contract):
    path: RelativePath
    revision: NonNegativeInt


class FileList(Contract):
    workspace_revision: NonNegativeInt
    files: list[FileEntry]


class FileContent(FileEntry):
    content: str


class FileMutation(Contract):
    path: RelativePath
    expected_revision: NonNegativeInt
    client_operation_id: UUID


class FileWrite(FileMutation):
    content: str


class FileCreate(Contract):
    path: RelativePath
    content: str
    expected_workspace_revision: NonNegativeInt
    client_operation_id: UUID


class FileRename(FileMutation):
    destination: RelativePath


class FileRevision(FileEntry):
    workspace_revision: NonNegativeInt
    content_sha256: Sha256
    saved_at: UtcTime


class ExecutionRequest(Contract):
    command_id: Text
    workspace_revision: NonNegativeInt
    client_operation_id: UUID


class ExecutionResult(Contract):
    execution_id: UUID
    workspace_revision: NonNegativeInt
    command: Annotated[list[str], Field(min_length=1)]
    status: Literal["COMPLETED", "TIMED_OUT", "FAILED"]
    exit_code: int | None
    duration_ms: NonNegativeInt
    stdout_artifact_id: UUID
    stderr_artifact_id: UUID


class TerminalTicket(Contract):
    ticket: Text
    expires_at: UtcTime


class TerminalInput(Contract):
    type: Literal["input"]
    data: str


class TerminalOutput(Contract):
    type: Literal["output"]
    data: str


class TerminalResize(Contract):
    type: Literal["resize"]
    rows: PositiveInt
    cols: PositiveInt


class TerminalHeartbeat(Contract):
    type: Literal["heartbeat"]


class TerminalClose(Contract):
    type: Literal["close"]
    reason: Text


class UserMessage(Contract):
    role: Literal["user"]
    content: Text


class RepositoryContext(Contract):
    workspace_revision: NonNegativeInt
    file_paths: list[RelativePath]


class AIRequest(Contract):
    messages: Annotated[list[UserMessage], Field(min_length=1)]
    context: RepositoryContext


class AIReply(Contract):
    interaction_id: UUID
    model: Text
    content: str


class RecordingConsent(Contract):
    notice_version: Text
    granted: bool


class AudioChunk(Contract):
    type: Literal["audio_chunk"]
    stream_id: UUID
    sequence: NonNegativeInt
    start_ms: NonNegativeInt
    audio_base64: Annotated[str, Field(min_length=4, max_length=131072)]


class AudioAck(Contract):
    type: Literal["audio_ack"]
    stream_id: UUID
    sequence: NonNegativeInt


class TranscriptSegment(Contract):
    type: Literal["transcript_segment"]
    segment_id: UUID
    start_ms: NonNegativeInt
    end_ms: NonNegativeInt
    text: Text
    is_final: bool
    language: Text
    transcription_model: Text

    @model_validator(mode="after")
    def validate_interval(self) -> Self:
        if self.end_ms < self.start_ms:
            raise ValueError("segment ends before start")
        return self


class TranscriptCorrection(WrittenReasoning):
    reason: Text


class EvidenceReceipt(Contract):
    event_id: UUID
    server_sequence: PositiveInt


type EvidenceValue = (
    str | int | float | bool | None | list[EvidenceValue] | dict[str, EvidenceValue]
)


class EvidenceEvent(EvidenceReceipt):
    session_id: UUID
    stage_id: StageId | None
    stage_attempt_id: UUID | None
    event_type: Text
    source: Literal[
        "browser",
        "control_plane",
        "sandbox_broker",
        "ai_gateway",
        "transcription",
        "evaluator",
        "reviewer",
    ]
    occurred_at: UtcTime
    received_at: UtcTime
    schema_version: PositiveInt
    deduplication_id: UUID
    payload: dict[str, EvidenceValue]
    artifact_id: UUID | None = None
    artifact_sha256: Sha256 | None = None

    @model_validator(mode="after")
    def validate_stage(self) -> Self:
        if (self.stage_id is None) != (self.stage_attempt_id is None):
            raise ValueError("stage ID and attempt ID must be supplied together")
        if self.artifact_sha256 and self.artifact_id is None:
            raise ValueError("artifact hash requires artifact ID")
        return self


class EventPage(Contract):
    events: list[EvidenceEvent]
    next_cursor: str | None


class Snapshot(Contract):
    snapshot_id: UUID
    session_id: UUID
    assessment_version_id: UUID
    stage_id: StageId | None
    stage_attempt_id: UUID | None
    purpose: Literal["initial", "stage_seal", "submission"]
    workspace_revision: NonNegativeInt
    source_sha256: Sha256
    image_digest: ImageDigest
    created_at: UtcTime


class Rating(Contract):
    criterion_id: Text
    dimension: Literal["independent", "assisted"]
    score: Annotated[int, Field(ge=1, le=5)] | None
    rationale: Text
    evidence_ids: list[UUID]

    @model_validator(mode="after")
    def require_evidence_for_rating(self) -> Self:
        if self.score is not None and not self.evidence_ids:
            raise ValueError("a score needs cited evidence")
        return self


class Report(Contract):
    report_id: UUID
    session_id: UUID
    rubric_version: Text
    ratings: list[Rating]
    integrity_controls: list[Text]
    limitations: list[Text]
    revision: NonNegativeInt
    finalized_at: UtcTime | None

    @model_validator(mode="after")
    def require_limitations_on_finalized(self) -> Self:
        if self.finalized_at is not None and not self.limitations:
            raise ValueError("finalized report must document integrity limitations")
        return self


class FinalizeReview(Contract):
    expected_revision: NonNegativeInt


class ReviewRating(Contract):
    expected_revision: NonNegativeInt
    rating: Rating


class ReportPage(Contract):
    reports: list[Report]
    next_cursor: str | None


class RubricCriterion(Contract):
    criterion_id: Text
    dimension: Literal["independent", "assisted"]
    description: Text
    anchors: list[str]


class ReviewerRubric(Contract):
    rubric_version: Text
    criteria: list[RubricCriterion]
