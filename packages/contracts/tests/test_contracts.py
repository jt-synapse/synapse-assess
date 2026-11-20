import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError
from synapse_contracts import models as m
from synapse_contracts.catalog import ENDPOINTS
from synapse_contracts.generate import PACKAGE, artifacts

FIXTURES = json.loads((PACKAGE / "fixtures/shared.json").read_text())


@pytest.mark.parametrize("fixture", FIXTURES.values(), ids=FIXTURES.keys())
def test_shared_fixtures(fixture):
    model = getattr(m, fixture["type"])
    assert model.model_validate_json(json.dumps(fixture["value"]))


def test_generated_artifacts_match_current_models():
    for name, contents in artifacts().items():
        assert (PACKAGE / "generated" / name).read_text() == contents


@pytest.mark.parametrize("name", ["backendManifest", "minimalManifest"])
def test_draft_requires_verified_digests_for_publication(name):
    raw = deepcopy(FIXTURES[name]["value"])
    with pytest.raises(ValueError, match="publication"):
        m.AssessmentManifest.model_validate(raw).require_published()
    raw["runtime"]["image_digest"] = "sha256:" + "1" * 64
    for material in ("candidate_artifact", "evaluator_artifact"):
        raw[material]["sha256"] = "2" * 64
    assert (
        m.AssessmentManifest.model_validate(raw).require_published().package_id == raw["package_id"]
    )


@pytest.mark.parametrize(
    "path", [".", "../private", "/tmp", "safe/../private", "safe//file", "x\\file", "C:/file"]
)
def test_lexically_unsafe_paths_rejected(path):
    with pytest.raises(ValidationError):
        m.FileEntry(path=path, revision=1)


def test_evaluator_material_must_be_separate():
    raw = deepcopy(FIXTURES["backendManifest"]["value"])
    raw["evaluator_artifact"]["path"] = "candidate/private"
    with pytest.raises(ValidationError, match="disjoint"):
        m.AssessmentManifest.model_validate(raw)


def test_invalid_policies_and_duplicate_stage_ids_are_rejected():
    raw = deepcopy(FIXTURES["backendManifest"]["value"])
    raw["stages"][0]["ai_enabled"] = True
    with pytest.raises(ValidationError, match="assisted stage"):
        m.AssessmentManifest.model_validate(raw)
    raw["stages"][0]["ai_enabled"] = False
    raw["stages"][1]["stage_id"] = "debug"
    with pytest.raises(ValidationError, match="unique"):
        m.AssessmentManifest.model_validate(raw)


def test_stage_and_timestamp_evidence():
    raw = deepcopy(FIXTURES["event"]["value"])
    raw["occurred_at"] = "2026-11-19T05:00:00-05:00"
    assert m.EvidenceEvent.model_validate(raw).occurred_at.hour == 10
    raw["stage_attempt_id"] = None
    with pytest.raises(ValidationError, match="together"):
        m.EvidenceEvent.model_validate(raw)
    raw["stage_id"] = None
    raw["occurred_at"] = "2026-11-19T05:00:00"
    with pytest.raises(ValidationError):
        m.EvidenceEvent.model_validate(raw)


def test_candidate_inputs_reject_evaluator_and_server_fields():
    raw = {
        "path": "sample",
        "expected_revision": 1,
        "content": "x",
        "client_operation_id": FIXTURES["event"]["value"]["event_id"],
        "server_sequence": 2,
    }
    with pytest.raises(ValidationError):
        m.FileWrite.model_validate(raw)
    with pytest.raises(ValidationError):
        m.Session.model_validate({"evaluator_artifact": {"path": "private"}})
    model = m.Rating(
        criterion_id="c",
        dimension="independent",
        score=None,
        rationale="No observed evidence",
        evidence_ids=[],
    )
    with pytest.raises(ValidationError, match="cited evidence"):
        m.Rating.model_validate(dict(model.model_dump(), score=4))


def test_all_spec_refs_resolve_and_planned_endpoints_are_explicit():
    spec = json.loads((PACKAGE / "generated/openapi.json").read_text())

    def verify(value):
        if isinstance(value, dict):
            if "$ref" in value:
                obj = spec
                for part in value["$ref"].removeprefix("#/").split("/"):
                    obj = obj[part]
            for child in value.values():
                verify(child)
        elif isinstance(value, list):
            for child in value:
                verify(child)

    verify(spec)
    assert len({endpoint.name for endpoint in ENDPOINTS}) == len(ENDPOINTS)
    for path, methods in spec["paths"].items():
        for op in methods.values():
            assert op["x-availability"] == ("served" if "/health/" in path else "planned")
            assert bool(op["security"]) == (op["x-caller"] != "public")
    endpoints = spec["paths"]
    assert (
        endpoints["/api/v1/sessions/{id}/files/content"]["put"]["responses"]["409"]["description"]
        == "WORKSPACE_REVISION_CONFLICT"
    )
    assert "candidate" not in endpoints["/api/v1/sessions/{id}/report"]["get"]["x-caller"]
    assert {path.rsplit("/", 2)[1] for path in spec["x-websockets"]} == {"terminal", "audio"}


def test_orderflow_source_manifest_matches_platform_contract():
    path = Path(__file__).resolve().parents[3] / "assessments/001-orderflow/manifest.yaml"
    assert m.AssessmentManifest.model_validate_json(path.read_text()).services == ["postgresql"]


def test_public_spec_excludes_private_package_materials():
    spec = json.loads((PACKAGE / "generated/openapi.json").read_text())
    assert "AssessmentManifest" not in spec["components"]["schemas"]
    assert "evaluator_artifact" not in json.dumps(spec)
    raw = deepcopy(FIXTURES["backendManifest"]["value"])
    raw["stages"][0]["instructions_path"] = "evaluator/hidden.md"
    with pytest.raises(ValidationError, match="evaluator materials"):
        m.AssessmentManifest.model_validate(raw)


def test_served_operation_contracts_match_fastapi():
    from synapse_api.main import app

    runtime = app.openapi()
    design = json.loads((PACKAGE / "generated/openapi.json").read_text())
    served = {
        (path, method): op
        for path, methods in design["paths"].items()
        for method, op in methods.items()
        if op["x-availability"] == "served"
    }
    actual = {
        (path, method): op
        for path, methods in runtime["paths"].items()
        for method, op in methods.items()
    }
    assert actual.keys() == served.keys()
    for key, op in actual.items():
        assert served[key]["operationId"] == op["operationId"]
        assert served[key]["responses"].keys() == op["responses"].keys()
        for code, entry in op["responses"].items():
            schema = entry["content"]["application/json"]["schema"]
            assert schema == served[key]["responses"][code]["content"]["application/json"]["schema"]
            name = schema["$ref"].split("/")[-1]
            assert runtime["components"]["schemas"][name] == design["components"]["schemas"][name]


def test_published_instructions_are_bound_to_the_release():
    raw = deepcopy(FIXTURES["backendManifest"]["value"])
    raw["runtime"]["image_digest"] = "sha256:" + "1" * 64
    raw["candidate_artifact"]["sha256"] = "2" * 64
    raw["evaluator_artifact"]["sha256"] = "3" * 64
    raw["stages"][0]["instructions_path"] = "instructions/first.md"
    with pytest.raises(ValueError, match="digest for each stage"):
        m.AssessmentManifest.model_validate(raw).require_published()
    raw["stages"][0]["instructions_sha256"] = "4" * 64
    assert m.AssessmentManifest.model_validate(raw).require_published()


def test_finalized_report_requires_integrity_limitations_and_audio_frames_discriminate():
    report = deepcopy(FIXTURES["finalizedReport"]["value"])
    assert m.Report.model_validate(report).limitations
    report["limitations"] = []
    with pytest.raises(ValidationError, match="integrity limitations"):
        m.Report.model_validate(report)
    report["finalized_at"] = None
    assert m.Report.model_validate(report).finalized_at is None

    segment = deepcopy(FIXTURES["transcriptSegment"]["value"])
    segment["is_final"] = False
    assert not m.TranscriptSegment.model_validate(segment).is_final
    segment["end_ms"] = 500
    with pytest.raises(ValidationError, match="before start"):
        m.TranscriptSegment.model_validate(segment)
