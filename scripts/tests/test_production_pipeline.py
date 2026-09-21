"""Offline production handoffs, approval binding, and independent concept work."""
import json
import subprocess
import sys

import pytest

from test_work_packets import (project, run, document, proof, add, finish, finish_data,
                               verify_environment, reconciliation, progress_data, snapshot)
import work_packets as wp
import run_state as rs


def completed(project, run, identifier="blockout", **fields):
    add(project, run, identifier, **fields)
    wp.start(project, run, packet=identifier)
    finish(project, run, identifier)


def review_data(project, run, **overrides):
    state = rs.load_run(project, run)
    phase = state["pipeline"]["phase"]
    specs = wp._metadata(run, state)
    included = [key for key, value in state["packets"].items()
                if specs[key]["phase"] == phase and value["status"] == "completed"]
    return {"phase": phase, "summary": "Review the demonstrated result and chosen direction.",
            "playable": {"level": state["environment"]["contract"]["target_level"],
                         "launch_instructions": "Open the test level and start PIE.", "controls": "WASD and E.",
                         "objectives": "Collect one item and reach the exit.", "known_issues": [],
                         "runtime_status": "pass", "runtime_evidence": proof(run, f"{phase}-runtime.txt", "Synthetic runtime test passed")},
            "included_packets": included, "deferred_packets": {},
            "checks": [{"id": key, "status": "pass", "evidence": proof(run, f"{phase}-{key}.txt", f"Observed {key}")}
                       for key in sorted(wp.PHASE_CHECKS[phase])], **overrides}


def review(project, run, **overrides):
    return wp.phase_review(project, run, evidence=document(run, "review.json", review_data(project, run, **overrides)))


def approve(project, run, **overrides):
    report = wp.status(project, run)
    data = {"decision": "approved", "approved_by": "user", "user_message": "Approve this reviewed phase.",
            "human_evaluation": {"played": True, "feedback": "Synthetic user tested the route and accepts the result.",
                                 "evidence": proof(run, "human-playtest.txt", "Synthetic user playtest feedback")},
            "review_fingerprint": report["pipeline"]["review"]["fingerprint"],
            "proof": [proof(run, "approval-message.txt", "Synthetic test user: approve this reviewed phase.")], **overrides}
    return wp.phase_approve(project, run, evidence=document(run, "approval.json", data))


def test_future_phase_cannot_start_or_skip_approval(project, run):
    verify_environment(project, run)
    add(project, run, "later", phase="production")
    with pytest.raises(rs.StateError, match="active production phase"):
        wp.start(project, run, packet="later")
    with pytest.raises(rs.StateError, match="user approval"):
        wp.phase_advance(project, run)
    assert wp.status(project, run)["pipeline"]["phase"] == "pre-production"


def test_three_phase_lifecycle_and_final_scope_acceptance(project, run):
    verify_environment(project, run)
    for phase in wp.PHASES:
        completed(project, run, identifier=phase)
        assert review(project, run)["pipeline"]["status"] == "awaiting_approval"
        with pytest.raises(rs.StateError, match="user approval"):
            wp.phase_advance(project, run)
        assert approve(project, run)["pipeline"]["status"] == "approved"
        report = wp.phase_advance(project, run)
    assert report["pipeline"]["phase"] == "post-production"
    assert report["pipeline"]["status"] == "complete"
    assert report["mission_status"] == "not_assessed"
    with pytest.raises(rs.StateError, match="complete"):
        add(project, run, "more")
    history = rs.load_run(project, run)["pipeline"]["history"]
    assert len([item for item in history if item["event"] == "advance"]) == 3


@pytest.mark.parametrize("overrides", [{"approved_by": "director"}, {"decision": "pending"},
                                       {"user_message": ""}, {"review_fingerprint": "older-review"}, {"proof": []}])
def test_approval_requires_exact_user_record(project, run, overrides):
    verify_environment(project, run)
    completed(project, run)
    review(project, run)
    before = (run / "run.json").read_bytes()
    with pytest.raises(rs.StateError):
        approve(project, run, **overrides)
    assert (run / "run.json").read_bytes() == before


@pytest.mark.parametrize("when", ["before-approval", "after-approval"])
def test_review_invalidated_by_new_work(project, run, when):
    verify_environment(project, run)
    completed(project, run)
    review(project, run)
    if when == "after-approval":
        approve(project, run)
    add(project, run, "new-work")
    assert wp.status(project, run)["pipeline"]["status"] == "stale"
    with pytest.raises(rs.StateError, match="changed"):
        approve(project, run) if when == "before-approval" else wp.phase_advance(project, run)


@pytest.mark.parametrize("file", ["pre-production-core-loop.txt", "approval-message.txt", "result.txt"])
def test_changed_review_approval_or_result_evidence_blocks_advance(project, run, file):
    verify_environment(project, run)
    completed(project, run)
    review(project, run)
    approve(project, run)
    (run / "findings" / file).write_text("changed after review")
    with pytest.raises(rs.StateError, match="Evidence changed"):
        wp.phase_advance(project, run)


def test_review_cannot_hide_partial_work_or_skip_criteria(project, run):
    verify_environment(project, run)
    completed(project, run)
    add(project, run, "partial")
    with pytest.raises(rs.StateError, match="deferral"):
        review(project, run)
    with pytest.raises(rs.StateError, match="criterion"):
        review(project, run, deferred_packets={"partial": "Explicitly deferred for user decision"}, checks=[])
    report = review(project, run, deferred_packets={"partial": "Explicitly deferred for user decision"})
    assert report["pipeline"]["status"] == "awaiting_approval"
    approve(project, run)
    report = wp.phase_advance(project, run)
    assert any(item["id"] == "partial" and item["status"] == "pending" for item in report["queue"])
    with pytest.raises(rs.StateError, match="active production phase"):
        wp.start(project, run, packet="partial")


def test_review_requires_workers_to_settle_and_uncertainty_resolved(project, run):
    verify_environment(project, run)
    completed(project, run)
    add(project, run, "unfinished")
    wp.start(project, run, packet="unfinished")
    with pytest.raises(rs.StateError, match="Settle"):
        review(project, run)
    wp.progress(project, run, packet="unfinished", evidence=document(run, "progress.json", progress_data(uncertainty=True)))
    with pytest.raises(rs.StateError, match="Settle"):
        review(project, run)


def test_scope_exclusion_requires_reason_and_evidence(project, run):
    verify_environment(project, run)
    completed(project, run)
    data = review_data(project, run)
    data["checks"][0]["status"] = "not_applicable"
    with pytest.raises(rs.StateError, match="exclusion reason"):
        wp.phase_review(project, run, evidence=document(run, "review.json", data))
    data["checks"][0]["reason"] = "Explicitly excluded from this small capability test; user must review scope."
    assert wp.phase_review(project, run, evidence=document(run, "review.json", data))["pipeline"]["status"] == "awaiting_approval"


def add_concept(project, run, identifier="concept"):
    return add(project, run, identifier, lane="concept", role="environment-artist",
               allowed_changes=[f"concepts/{identifier}/"])


def test_concept_and_editor_can_run_together_but_editor_is_serial(project, run):
    add_concept(project, run)
    wp.start(project, run, packet="concept")  # Does not need a live editor.
    verify_environment(project, run)
    assert wp.status(project, run, packet="concept")["packet"]["status"] == "running"
    add(project, run, "blockout", role="layout-artist")
    wp.start(project, run, packet="blockout")
    add(project, run, "gameplay")
    with pytest.raises(rs.StateError, match="Another packet"):
        wp.start(project, run, packet="gameplay")
    add_concept(project, run, "second-concept")
    with pytest.raises(rs.StateError, match="Another packet"):
        wp.start(project, run, packet="second-concept")


@pytest.mark.parametrize("overrides", [{"role": "ai-programmer"}, {"allowed_changes": ["/Game/Map"]},
                                       {"allowed_changes": ["concepts/concept/../../outside"]}])
def test_concept_cannot_claim_editor_or_other_output_paths(project, run, overrides):
    values = {"lane": "concept", "role": "environment-artist", "allowed_changes": ["concepts/concept/"]}
    with pytest.raises(rs.StateError):
        add(project, run, "concept", **{**values, **overrides})


def test_concept_result_requires_owned_saved_outputs_and_survives_setup(project, run):
    add_concept(project, run)
    wp.start(project, run, packet="concept")
    data = finish_data(run)
    with pytest.raises(rs.StateError, match="nonempty"):
        wp.finish(project, run, packet="concept", evidence=document(run, "concept-finish.json", data))
    output = run / "concepts/concept/layout.svg"
    output.parent.mkdir(parents=True)
    output.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    data["outputs"] = ["concepts/concept/layout.svg"]
    wp.finish(project, run, packet="concept", evidence=document(run, "concept-finish.json", data))
    verify_environment(project, run)
    assert wp.status(project, run, packet="concept")["packet"]["status"] == "completed"
    output.write_text("changed concept")
    assert wp.status(project, run, packet="concept")["packet"]["status"] == "stale"


def test_cli_resume_includes_phase_and_never_advances(project, run):
    before = snapshot(run)
    result = subprocess.run([sys.executable, wp.__file__, "resume", "--project", str(project), "--run", str(run)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout)["pipeline"]["phase"] == "pre-production"
    assert snapshot(run) == before


@pytest.mark.parametrize("phase", wp.PHASES)
@pytest.mark.parametrize("change", [{"runtime_status": "not_run"}, {"level": "/Game/Wrong"},
                                    {"controls": ""}, {"known_issues": None}])
def test_every_phase_requires_concrete_playable_handoff(project, run, phase, change):
    verify_environment(project, run)
    # Reach the requested phase through normal accepted transitions.
    while wp.status(project, run)["pipeline"]["phase"] != phase:
        current = wp.status(project, run)["pipeline"]["phase"]
        completed(project, run, identifier=current)
        review(project, run)
        approve(project, run)
        wp.phase_advance(project, run)
    completed(project, run, identifier=phase)
    data = review_data(project, run)
    data["playable"].update(change)
    with pytest.raises(rs.StateError):
        wp.phase_review(project, run, evidence=document(run, "review.json", data))


@pytest.mark.parametrize("evaluation", [None, {"played": False}, {"played": True, "feedback": ""}])
def test_generic_approval_without_human_playtest_is_insufficient(project, run, evaluation):
    verify_environment(project, run)
    completed(project, run)
    review(project, run)
    with pytest.raises(rs.StateError):
        approve(project, run, human_evaluation=evaluation)
