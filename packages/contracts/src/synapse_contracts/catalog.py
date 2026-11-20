"""Design-time REST and WebSocket inventory. Never registers application routes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from . import models as m

Model = type[m.Contract]
S = "/api/v1/sessions/{id}"
OWN = "candidate:own-session"
REVIEW = "reviewer:assigned-session"
EMPLOYER = "employer:organization"
REPORT = "employer:organization or reviewer:assigned-session"


@dataclass(frozen=True)
class Endpoint:
    method: str
    path: str
    name: str
    access: str
    response: Model
    body: Model | None = None
    status: int = 200
    query: tuple[str, ...] = ()
    idempotent: bool = False
    conflict: str | None = None


ENDPOINTS = (
    Endpoint("get", "/api/v1/health/live", "liveness", "public", m.Liveness),
    Endpoint("get", "/api/v1/health/ready", "readiness", "public", m.Readiness),
    Endpoint(
        "post",
        "/api/v1/assessments/{id}/invitations",
        "inviteCandidate",
        EMPLOYER,
        m.Invitation,
        m.InviteRequest,
        201,
        idempotent=True,
    ),
    Endpoint(
        "post",
        "/api/v1/sessions",
        "createSession",
        "candidate:own-invitation",
        m.Session,
        m.CreateSession,
        201,
        idempotent=True,
    ),
    Endpoint("get", S, "readSession", OWN, m.Session),
    Endpoint("post", S + "/start", "startSession", OWN, m.Session, idempotent=True),
    Endpoint(
        "post",
        S + "/stages/complete",
        "completeCurrentStage",
        OWN,
        m.Session,
        m.StageCompletion,
        202,
        idempotent=True,
        conflict="STAGE_NOT_ACTIVE",
    ),
    Endpoint(
        "post",
        S + "/defense/answers",
        "recordDefenseAnswer",
        OWN,
        m.EvidenceReceipt,
        m.DefenseAnswer,
        201,
    ),
    Endpoint("post", S + "/submit", "submitSession", OWN, m.Session, status=202, idempotent=True),
    Endpoint("get", S + "/workspace", "readWorkspace", OWN, m.Workspace),
    Endpoint("get", S + "/files", "listFiles", OWN, m.FileList),
    Endpoint("get", S + "/files/content", "readFile", OWN, m.FileContent, query=("path",)),
    Endpoint(
        "put",
        S + "/files/content",
        "saveFile",
        OWN,
        m.FileRevision,
        m.FileWrite,
        conflict="WORKSPACE_REVISION_CONFLICT",
    ),
    Endpoint(
        "post",
        S + "/files",
        "createFile",
        OWN,
        m.FileRevision,
        m.FileCreate,
        201,
        conflict="WORKSPACE_REVISION_CONFLICT",
    ),
    Endpoint(
        "post",
        S + "/files/rename",
        "renameFile",
        OWN,
        m.FileRevision,
        m.FileRename,
        conflict="WORKSPACE_REVISION_CONFLICT",
    ),
    Endpoint(
        "delete",
        S + "/files",
        "deleteFile",
        OWN,
        m.Workspace,
        query=("path", "expected_revision", "client_operation_id"),
        conflict="WORKSPACE_REVISION_CONFLICT",
    ),
    Endpoint(
        "post",
        S + "/executions",
        "runApprovedCommand",
        OWN,
        m.ExecutionResult,
        m.ExecutionRequest,
        conflict="WORKSPACE_REVISION_CONFLICT",
    ),
    Endpoint(
        "post", S + "/terminal-tickets", "issueTerminalTicket", OWN, m.TerminalTicket, status=201
    ),
    Endpoint(
        "post", S + "/ai/messages", "sendAIMessage", OWN, m.AIReply, m.AIRequest, idempotent=True
    ),
    Endpoint(
        "post",
        S + "/reasoning/consent",
        "recordConsent",
        OWN,
        m.EvidenceReceipt,
        m.RecordingConsent,
        idempotent=True,
    ),
    Endpoint(
        "post",
        S + "/reasoning/written",
        "recordWrittenReasoning",
        OWN,
        m.EvidenceReceipt,
        m.WrittenReasoning,
    ),
    Endpoint(
        "post",
        S + "/reasoning/transcripts/{segment_id}/corrections",
        "correctTranscript",
        OWN + " or " + REVIEW,
        m.EvidenceReceipt,
        m.TranscriptCorrection,
    ),
    Endpoint(
        "get",
        S + "/events",
        "readAuthorizedTimeline",
        OWN + " or " + REPORT,
        m.EventPage,
        query=("cursor",),
    ),
    Endpoint("get", S + "/review/rubric", "readReviewRubric", REVIEW, m.ReviewerRubric),
    Endpoint(
        "post",
        S + "/review/ratings",
        "appendReviewerRating",
        REVIEW,
        m.Report,
        m.ReviewRating,
        idempotent=True,
        conflict="REVIEW_REVISION_CONFLICT",
    ),
    Endpoint(
        "post",
        S + "/review/finalize",
        "finalizeReport",
        REVIEW,
        m.Report,
        m.FinalizeReview,
        idempotent=True,
        conflict="REVIEW_REVISION_CONFLICT",
    ),
    Endpoint("get", S + "/report", "readReport", REPORT, m.Report),
    Endpoint("get", "/api/v1/reports", "listReports", REPORT, m.ReportPage, query=("cursor",)),
)


def ref(model: Model) -> dict[str, str]:
    return {"$ref": "#/components/schemas/" + model.__name__}


def response(model: Model, description: str) -> dict[str, Any]:
    return {"description": description, "content": {"application/json": {"schema": ref(model)}}}


def operation(endpoint: Endpoint) -> dict[str, Any]:
    is_public = endpoint.access == "public"
    responses = {str(endpoint.status): response(endpoint.response, "Success")}
    if not is_public:
        for status, label in {
            "401": "Authentication required",
            "403": "Access or stage denied",
            "404": "Resource unavailable",
            "422": "Invalid request",
        }.items():
            responses[status] = response(m.ErrorEnvelope, label)
    if endpoint.conflict:
        responses["409"] = response(m.ErrorEnvelope, endpoint.conflict)
    if endpoint.name == "readiness":
        responses["503"] = response(m.ErrorEnvelope, "DEPENDENCY_UNAVAILABLE")
    op: dict[str, Any] = {
        "operationId": endpoint.name,
        "x-availability": "served" if is_public else "planned",
        "x-caller": endpoint.access,
        "security": [] if is_public else [{"sessionAuth": []}],
        "responses": responses,
    }
    if endpoint.name == "readAuthorizedTimeline":
        op["description"] = (
            "Apply tenant, session, source and event visibility filtering before pagination."
        )
    parameters: list[dict[str, Any]] = [
        {
            "in": "path",
            "name": name,
            "required": True,
            "schema": {"type": "string", "format": "uuid"},
        }
        for name in re.findall(r"{(\w+)}", endpoint.path)
    ]
    for name in endpoint.query:
        schema: dict[str, Any] = {"type": "string"}
        if name == "client_operation_id":
            schema["format"] = "uuid"
        elif name == "expected_revision":
            schema = {"type": "integer", "minimum": 0}
        parameters.append(
            {"in": "query", "name": name, "required": name != "cursor", "schema": schema}
        )
    if endpoint.idempotent:
        parameters.append(
            {
                "in": "header",
                "name": "Idempotency-Key",
                "required": True,
                "schema": {"type": "string", "minLength": 1},
            }
        )
    if parameters:
        op["parameters"] = parameters
    if endpoint.body:
        op["requestBody"] = {
            "required": True,
            "content": {"application/json": {"schema": ref(endpoint.body)}},
        }
    return op


def openapi(schemas: dict[str, Any]) -> dict[str, Any]:
    paths: dict[str, Any] = {}
    for endpoint in ENDPOINTS:
        paths.setdefault(endpoint.path, {})[endpoint.method] = operation(endpoint)
    spec: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": "Synapse Assess contracts",
            "version": "1.0.0",
            "description": "Design inventory. Each operation declares its implementation status.",
        },
        "paths": paths,
        "components": {
            "schemas": schemas,
            "securitySchemes": {
                "sessionAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "Short-lived access credential",
                }
            },
        },
        "x-websockets": {
            S + "/terminal/ws": {
                "x-availability": "planned",
                "x-caller": OWN,
                "authorization": "Redeem one expiring session-and-sandbox-bound ticket before opening the PTY.",
                "clientFrames": [
                    ref(m.TerminalInput),
                    ref(m.TerminalResize),
                    ref(m.TerminalHeartbeat),
                    ref(m.TerminalClose),
                ],
                "serverFrames": [
                    ref(m.TerminalOutput),
                    ref(m.TerminalHeartbeat),
                    ref(m.TerminalClose),
                ],
            },
            S + "/reasoning/audio/ws": {
                "x-availability": "planned",
                "x-caller": OWN,
                "authorization": "Authenticate session, check origin, current stage and active consent before accepting audio.",
                "clientFrames": [ref(m.AudioChunk)],
                "serverFrames": [ref(m.AudioAck), ref(m.TranscriptSegment)],
            },
        },
    }

    # Ship only reachable HTTP and stream types. Private build manifests remain outside the API.
    reachable: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
        if isinstance(value, dict):
            if "$ref" in value:
                name = value["$ref"].rsplit("/", 1)[-1]
                if name not in reachable:
                    reachable.add(name)
                    visit(schemas[name])
            for child in value.values():
                visit(child)

    visit(paths)
    visit(spec["x-websockets"])
    spec["components"]["schemas"] = {key: schemas[key] for key in sorted(reachable)}
    return spec
