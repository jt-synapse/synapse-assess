// Generated from fixtures/shared.json for a TypeScript consumer check.
import type * as Contract from "./index";

export const backendManifest = {
  "schema_version": 1,
  "package_id": "backend-demo",
  "version": "1.0.0",
  "title": "Backend fixture",
  "runtime": {
    "image": "fixtures/backend",
    "image_digest": null
  },
  "services": [
    "postgresql"
  ],
  "stages": [
    {
      "stage_id": "debug",
      "kind": "independent",
      "duration_minutes": 35,
      "ai_enabled": false
    },
    {
      "stage_id": "extend",
      "kind": "assisted",
      "duration_minutes": 40,
      "ai_enabled": true
    }
  ],
  "candidate_artifact": {
    "path": "candidate",
    "sha256": null
  },
  "evaluator_artifact": {
    "path": "evaluator",
    "sha256": null
  }
} satisfies Contract.AssessmentManifest;
export const minimalManifest = {
  "schema_version": 1,
  "package_id": "filesystem-demo",
  "version": "1.0.0",
  "title": "Filesystem fixture",
  "runtime": {
    "image": "fixtures/minimal",
    "image_digest": null
  },
  "services": [],
  "stages": [
    {
      "stage_id": "edit",
      "kind": "independent",
      "duration_minutes": 10,
      "ai_enabled": false
    }
  ],
  "candidate_artifact": {
    "path": "starter",
    "sha256": null
  },
  "evaluator_artifact": {
    "path": "private",
    "sha256": null
  }
} satisfies Contract.AssessmentManifest;
export const saveConflict = {
  "error": {
    "code": "WORKSPACE_REVISION_CONFLICT",
    "message": "The file has a newer revision.",
    "request_id": "00000000-0000-4000-8000-000000000001"
  }
} satisfies Contract.ErrorEnvelope;
export const stageDenied = {
  "error": {
    "code": "STAGE_NOT_ACTIVE",
    "message": "This operation requires an active stage.",
    "request_id": "00000000-0000-4000-8000-000000000002"
  }
} satisfies Contract.ErrorEnvelope;
export const event = {
  "event_id": "00000000-0000-4000-8000-000000000001",
  "session_id": "00000000-0000-4000-8000-000000000002",
  "stage_id": "debug",
  "stage_attempt_id": "00000000-0000-4000-8000-000000000003",
  "server_sequence": 1,
  "schema_version": 1,
  "deduplication_id": "00000000-0000-4000-8000-000000000004",
  "occurred_at": "2026-11-19T10:00:00Z",
  "received_at": "2026-11-19T10:00:01Z",
  "event_type": "workspace.file.saved",
  "source": "sandbox_broker",
  "payload": {
    "revision": 1
  }
} satisfies Contract.EvidenceEvent;
export const audioAck = {
  "type": "audio_ack",
  "stream_id": "00000000-0000-4000-8000-000000000005",
  "sequence": 0
} satisfies Contract.AudioAck;
export const transcriptSegment = {
  "type": "transcript_segment",
  "segment_id": "00000000-0000-4000-8000-000000000006",
  "start_ms": 1000,
  "end_ms": 2500,
  "text": "Checking inventory update atomicity.",
  "is_final": true,
  "language": "en",
  "transcription_model": "stt-fixture-v1"
} satisfies Contract.TranscriptSegment;
export const finalizedReport = {
  "report_id": "00000000-0000-4000-8000-000000000007",
  "session_id": "00000000-0000-4000-8000-000000000002",
  "rubric_version": "1.0.0",
  "ratings": [
    {
      "criterion_id": "concurrency",
      "dimension": "independent",
      "score": 4,
      "rationale": "Atomic conditional update verified under concurrent transactions.",
      "evidence_ids": [
        "00000000-0000-4000-8000-000000000001"
      ]
    }
  ],
  "integrity_controls": [
    "Platform AI disabled in Stage A",
    "Server-enforced stage sealing"
  ],
  "limitations": [
    "Remote assessments cannot guarantee the absence of external devices."
  ],
  "revision": 1,
  "finalized_at": "2026-11-19T12:00:00Z"
} satisfies Contract.Report;
