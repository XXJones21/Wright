import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_state as rs
import work_packets as wp


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "Project"
    root.mkdir()
    (root / "Example.uproject").write_text("{}")
    return root


@pytest.fixture
def run(project):
    report = wp.init(project, task="small-outcome", target_level="/Game/Wright/TestRoom", plugin_revision="test")
    return Path(report["run_dir"])


def document(run, name, data):
    path = run / "findings" / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def proof(run, name="proof.txt", content="observed state"):
    path = run / "findings" / name
    path.write_text(content, encoding="utf-8")
    return path.relative_to(run).as_posix()


def environment_data(project, run, **overrides):
    return {"observed_project": str(project / "Example.uproject"), "observed_level": "/Game/Wright/TestRoom",
            "level_created_for_run": True, "persistence_verified": True, "evidence": [proof(run, "environment.txt")], **overrides}


def verify_environment(project, run):
    return wp.environment(project, run, evidence=document(run, "environment.json", environment_data(project, run)))


def spec(identifier="one", kind="change", dependencies=(), **overrides):
    return {"id": identifier, "kind": kind, "outcome": f"Verify small outcome {identifier}",
            "depends_on": list(dependencies), "allowed_changes": [] if kind == "probe" else ["run-owned test actor"],
            "checks": [{"id": "observed", "description": "Expected outcome is observed"}],
            "budget": {"tool_calls": 5, "minutes": 2}, **overrides}


def add(project, run, identifier="one", kind="change", dependencies=(), **overrides):
    return wp.add(project, run, spec=document(run, f"{identifier}-spec.json", spec(identifier, kind, dependencies, **overrides)))


def progress_data(**overrides):
    return {"tool_calls": 1, "elapsed_seconds": 10, "objects": ["/Game/Wright/TestObject"],
            "next_action": "Read back the object", "uncertainty": False, **overrides}


def finish_data(run, kind="change", **overrides):
    evidence = proof(run, "result.txt")
    return {"checks": [{"id": "observed", "status": "pass", "evidence": evidence}],
            "persistence": {"status": "verified", "evidence": evidence} if kind == "change" else {"status": "not_applicable"},
            "tool_calls": 2, "elapsed_seconds": 20, **overrides}


def finish(project, run, identifier="one", kind="change", **overrides):
    return wp.finish(project, run, packet=identifier,
                     evidence=document(run, f"{identifier}-finish.json", finish_data(run, kind, **overrides)))


def reconciliation(run, **overrides):
    return document(run, "reconcile.json", {"reason": "Read-back proved exact current state", "proof": [proof(run, "reconcile.txt")],
                                            "objects": ["/Game/Wright/TestObject"], "next_action": "Continue remaining verification",
                                            "uncertainty": False, **overrides})


def snapshot(run):
    return {str(path.relative_to(run)): (path.stat().st_mtime_ns, path.read_bytes()) for path in run.rglob("*") if path.is_file()}


def test_environment_is_explicit_and_initially_unverified(project, run):
    report = wp.status(project, run)
    assert report["workflow"] == "packets-v1"
    assert report["environment"]["status"] == "unverified"
    assert report["environment"]["level_mode"] == "isolated"
    assert report["environment"]["target_level"] == "/Game/Wright/TestRoom"
    assert report["overall"] == "incomplete" and report["mission_status"] == "not_assessed"
    assert rs.load_run(project, run)["baseline"] == {"status": "pending"}
    with pytest.raises(rs.StateError, match="target_level"):
        wp.init(project, task="invalid", target_level="current")
    with pytest.raises(rs.StateError, match="existing_level_reason"):
        wp.init(project, task="invalid", target_level="/Game/Existing", level_mode="existing")


def test_existing_mode_requires_explicit_reason_and_does_not_require_creation(project):
    report = wp.init(project, task="existing", target_level="/Game/Wright/TestRoom", level_mode="existing", existing_level_reason="User selected this test level")
    run = Path(report["run_dir"])
    data = environment_data(project, run, level_created_for_run=False)
    report = wp.environment(project, run, evidence=document(run, "env.json", data))
    assert report["environment"]["status"] == "verified"


def test_user_prepared_hyphenated_level_can_bind_without_new_level_creation(project):
    level = "/Game/Wright/codex_mission1-first-light/Level/L_Prototyping"
    report = wp.init(project, task="fresh-retry", target_level=level, level_mode="existing",
                     existing_level_reason="User prepared and explicitly selected this fresh test level")
    run = Path(report["run_dir"])
    data = environment_data(project, run, observed_level=level, level_created_for_run=False)
    report = wp.environment(project, run, evidence=document(run, "prepared-level.json", data))
    assert report["environment"]["status"] == "verified"
    assert report["environment"]["target_level"] == level
    add(project, run)
    assert wp.start(project, run, packet="one")["packet"]["status"] == "running"


@pytest.mark.parametrize("level", ["/Game/Wright/../Other", "/Game/Wright//Map", "/Game/Wright/Map.Map", "/Game/Wright/Map/", "C:/Content/Map"])
def test_level_path_relaxation_does_not_allow_traversal_or_object_paths(project, level):
    with pytest.raises(rs.StateError, match="target_level"):
        wp.init(project, task="invalid-map", target_level=level)


@pytest.mark.parametrize("field,value,error", [
    ("observed_project", "Other.uproject", "project"),
    ("observed_level", "/Game/Other", "target level"),
    ("persistence_verified", False, "persistence"),
    ("level_created_for_run", False, "Isolated"),
    ("evidence", [], "nonempty"),
    ("evidence", ["../../outside.txt"], "traversal"),
])
def test_environment_rejects_mismatch_or_missing_proof(project, run, field, value, error):
    source = document(run, "env.json", environment_data(project, run, **{field: value}))
    before = snapshot(run)
    with pytest.raises(rs.StateError, match=error):
        wp.environment(project, run, evidence=source)
    assert snapshot(run) == before


def test_empty_evidence_and_external_source_rejected(project, run, tmp_path):
    data = environment_data(project, run)
    (run / data["evidence"][0]).write_text("")
    with pytest.raises(rs.StateError, match="nonempty file"):
        wp.environment(project, run, evidence=document(run, "env.json", data))
    source = tmp_path / "external.json"
    source.write_text(json.dumps(spec()))
    with pytest.raises(rs.StateError, match="inside"):
        wp.add(project, run, spec=source)


def test_change_cannot_start_before_environment_but_probe_can(project, run):
    add(project, run)
    with pytest.raises(rs.StateError, match="unverified"):
        wp.start(project, run, packet="one")
    add(project, run, "setup-probe", "probe")
    report = wp.start(project, run, packet="setup-probe")
    assert report["packet"]["status"] == "running"
    report = finish(project, run, "setup-probe", "probe")
    assert report["packet"]["status"] == "completed"
    assert report["overall"] == "incomplete"
    assert report["packet"]["result"]["document"]["sha256"]


@pytest.mark.parametrize("overrides,error", [
    ({"kind": "probe", "allowed_changes": ["write actor"]}, "Probe changes"),
    ({"depends_on": ["missing"]}, "already be registered"),
    ({"depends_on": ["one"]}, "self dependency"),
    ({"checks": []}, "acceptance check"),
    ({"budget": {"tool_calls": 0, "minutes": 1}}, "positive"),
    ({"budget": {"tool_calls": True, "minutes": 1}}, "integer"),
])
def test_invalid_specs_rejected_before_registration(project, run, overrides, error):
    with pytest.raises(rs.StateError, match=error):
        add(project, run, **overrides)
    assert wp.status(project, run)["packet_count"] == 0


def test_packet_definitions_are_immutable_and_no_fixed_eight_limit(project, run):
    for index in range(10):
        add(project, run, identifier=f"packet-{index}", kind="probe")
    assert wp.status(project, run)["packet_count"] == 10
    with pytest.raises(rs.StateError, match="immutable"):
        add(project, run, identifier="packet-0", kind="probe")


def test_one_active_packet_and_no_implicit_restart(project, run):
    add(project, run, "one", "probe")
    add(project, run, "two", "probe")
    wp.start(project, run, packet="one")
    with pytest.raises(rs.StateError, match="Another packet"):
        wp.start(project, run, packet="two")
    with pytest.raises(rs.StateError, match="reconcile"):
        wp.start(project, run, packet="one")


def test_progress_consumes_budget_and_reconcile_extends_without_reset(project, run):
    add(project, run, kind="probe")
    wp.start(project, run, packet="one")
    report = wp.progress(project, run, packet="one", evidence=document(run, "progress.json", progress_data(tool_calls=5)))
    assert report["packet"]["status"] == "paused"
    with pytest.raises(rs.StateError, match="reconcile"):
        wp.start(project, run, packet="one")
    with pytest.raises(rs.StateError, match="Budget exhausted"):
        wp.reconcile(project, run, packet="one", evidence=reconciliation(run))
    report = wp.reconcile(project, run, packet="one", evidence=reconciliation(run, budget_extension={"tool_calls": 3, "minutes": 1}))
    assert report["packet"]["status"] == "running"
    assert report["packet"]["effective_budget"] == {"tool_calls": 8, "minutes": 3}
    assert report["packet"]["metrics"]["tool_calls"] == 5
    with pytest.raises(rs.StateError, match="may not decrease"):
        wp.progress(project, run, packet="one", evidence=document(run, "progress.json", progress_data()))
    report = finish(project, run, kind="probe", tool_calls=6)
    assert report["packet"]["status"] == "completed"


def test_elapsed_budget_and_uncertain_mutation_pause_before_more_work(project, run):
    verify_environment(project, run)
    add(project, run)
    wp.start(project, run, packet="one")
    report = wp.progress(project, run, packet="one", evidence=document(run, "progress.json", progress_data(uncertainty=True)))
    assert report["packet"]["status"] == "paused" and report["packet"]["uncertainty"] is True
    add(project, run, "two")
    with pytest.raises(rs.StateError, match="uncertain writes"):
        wp.start(project, run, packet="two")
    with pytest.raises(rs.StateError, match="running packet"):
        finish(project, run)
    with pytest.raises(rs.StateError, match="resolve uncertainty"):
        wp.reconcile(project, run, packet="one", evidence=reconciliation(run, uncertainty=True))
    wp.reconcile(project, run, packet="one", evidence=reconciliation(run))
    report = wp.progress(project, run, packet="one", evidence=document(run, "progress.json", progress_data(elapsed_seconds=121)))
    assert report["packet"]["status"] == "paused" and "budget" in report["packet"]["pause_reason"]


def test_successful_atomic_completion_may_exceed_soft_budget(project, run):
    add(project, run, kind="probe")
    wp.start(project, run, packet="one")
    report = finish(project, run, kind="probe", tool_calls=6, elapsed_seconds=140)
    assert report["packet"]["status"] == "completed"
    assert report["packet"]["budget_exceeded"] is True
    assert report["overall"] == "registered_packets_complete"
    assert report["mission_status"] == "not_assessed"


def test_budget_paused_packet_can_finish_existing_proof_without_new_work(project, run):
    add(project, run, kind="probe")
    wp.start(project, run, packet="one")
    report = wp.progress(project, run, packet="one", evidence=document(run, "progress.json", progress_data(tool_calls=5)))
    assert report["packet"]["status"] == "paused"
    with pytest.raises(rs.StateError, match="already-gathered"):
        finish(project, run, kind="probe", tool_calls=6, elapsed_seconds=10)
    report = finish(project, run, kind="probe", tool_calls=5, elapsed_seconds=10)
    assert report["packet"]["status"] == "completed"
    assert report["packet"]["budget_exceeded"] is False


def test_budget_paused_finish_records_declared_finalization_overhead(project, run):
    add(project, run, kind="probe")
    wp.start(project, run, packet="one")
    wp.progress(project, run, packet="one", evidence=document(run, "progress.json", progress_data(tool_calls=5)))
    report = finish(project, run, kind="probe", tool_calls=7, elapsed_seconds=15, no_new_engine_work=True)
    assert report["packet"]["status"] == "completed"
    assert report["packet"]["budget_exceeded"] is True
    result = json.loads((run / report["packet"]["result"]["document"]["path"]).read_text())
    assert result["no_new_engine_work"] is True


@pytest.mark.parametrize("persistence_status", ["failed", "unknown"])
def test_persistence_failure_is_recorded_as_blocked_result(project, run, persistence_status):
    verify_environment(project, run)
    add(project, run)
    wp.start(project, run, packet="one")
    report = finish(project, run, persistence={"status": persistence_status, "evidence": proof(run, "save-failure.txt", "save did not verify")})
    assert report["packet"]["status"] == "blocked"
    assert report["overall"] == "incomplete"
    result = json.loads((run / report["packet"]["result"]["document"]["path"]).read_text())
    assert result["persistence"]["status"] == persistence_status


def test_compact_resume_inlines_verified_objects_and_next_action(project, run):
    add(project, run, kind="probe")
    wp.start(project, run, packet="one")
    data = progress_data(uncertainty=True)
    wp.progress(project, run, packet="one", evidence=document(run, "progress.json", data))
    report = wp.status(project, run)
    assert report["packet"]["objects"] == data["objects"]
    assert report["packet"]["next_action"] == data["next_action"]
    assert report["packet"]["uncertainty"] is True


def test_finish_requires_persistence_and_all_acceptance_results(project, run):
    verify_environment(project, run)
    add(project, run)
    wp.start(project, run, packet="one")
    with pytest.raises(rs.StateError, match="verified persistence"):
        finish(project, run, persistence={"status": "not_applicable"})
    with pytest.raises(rs.StateError, match="Every acceptance"):
        finish(project, run, checks=[])
    failed = [{"id": "observed", "status": "fail", "evidence": proof(run)}]
    report = finish(project, run, checks=failed)
    assert report["packet"]["status"] == "blocked" and report["overall"] == "incomplete"


def test_runtime_acceptance_cannot_be_satisfied_by_static_evidence(project, run):
    add(project, run, kind="probe", checks=[{"id": "observed", "description": "Actual runtime action works", "kind": "runtime"}])
    wp.start(project, run, packet="one")
    with pytest.raises(rs.StateError, match="actual evidence"):
        finish(project, run, kind="probe")
    runtime = {"status": "pass", "evidence": proof(run, "runtime.txt", "observed actual execution")}
    report = finish(project, run, kind="probe", runtime=runtime)
    result_path = run / report["packet"]["result"]["document"]["path"]
    assert json.loads(result_path.read_text())["runtime"]["status"] == "pass"


def test_sequential_dependency_proof_and_compact_status(project, run):
    verify_environment(project, run)
    add(project, run, "inspect", "probe")
    add(project, run, "build", "change", dependencies=["inspect"])
    with pytest.raises(rs.StateError, match="not completed"):
        wp.start(project, run, packet="build")
    wp.start(project, run, packet="inspect")
    finish(project, run, "inspect", "probe")
    wp.start(project, run, packet="build")
    report = finish(project, run, "build")
    assert report["overall"] == "registered_packets_complete"
    assert report["packet"]["dependencies"][0]["id"] == "inspect"
    assert "packets" not in report and "plan" not in report
    assert report["completed_count"] == 2


def test_stale_environment_proof_blocks_start_without_writing(project, run):
    verify_environment(project, run)
    add(project, run)
    (run / "findings" / "environment.txt").write_text("changed")
    before = snapshot(run)
    report = wp.status(project, run)
    assert report["environment"]["status"] == "unverified"
    with pytest.raises(rs.StateError, match="Evidence changed"):
        wp.start(project, run, packet="one")
    assert snapshot(run) == before


def test_changed_environment_requires_reconciliation_before_finish(project, run):
    verify_environment(project, run)
    add(project, run)
    wp.start(project, run, packet="one")
    data = environment_data(project, run)
    data["evidence"] = [proof(run, "new-environment.txt", "fresh observation")]
    wp.environment(project, run, evidence=document(run, "env-new.json", data))
    assert wp.status(project, run)["packet"]["status"] == "paused"
    with pytest.raises(rs.StateError, match="running packet"):
        finish(project, run)
    wp.reconcile(project, run, packet="one", evidence=reconciliation(run))
    assert finish(project, run)["packet"]["status"] == "completed"


def test_stale_completed_dependency_invalidates_downstream_readiness(project, run):
    add(project, run, "first", "probe")
    add(project, run, "second", "probe", dependencies=["first"])
    wp.start(project, run, packet="first")
    finish(project, run, "first", "probe")
    (run / "findings" / "result.txt").write_text("changed after acceptance")
    report = wp.status(project, run, packet="first")
    assert report["packet"]["status"] == "stale" and report["overall"] == "incomplete"
    with pytest.raises(rs.StateError, match="Evidence changed"):
        wp.start(project, run, packet="second")
    wp.reconcile(project, run, packet="first", evidence=reconciliation(run))
    finish(project, run, "first", "probe")
    assert wp.start(project, run, packet="second")["packet"]["status"] == "running"


def test_preflight_probe_becomes_stale_after_environment_binding(project, run):
    add(project, run, "discovery", "probe")
    add(project, run, "change", dependencies=["discovery"])
    wp.start(project, run, packet="discovery")
    finish(project, run, "discovery", "probe")
    verify_environment(project, run)
    report = wp.status(project, run, packet="discovery")
    assert report["packet"]["status"] == "stale"
    with pytest.raises(rs.StateError, match="stale environment"):
        wp.start(project, run, packet="change")
    wp.reconcile(project, run, packet="discovery", evidence=reconciliation(run))
    finish(project, run, "discovery", "probe")
    assert wp.start(project, run, packet="change")["packet"]["status"] == "running"


def test_verified_environment_probe_invalidated_by_environment_refresh(project, run):
    verify_environment(project, run)
    add(project, run, kind="probe")
    wp.start(project, run, packet="one")
    finish(project, run, kind="probe")
    data = environment_data(project, run, evidence=[proof(run, "refresh.txt", "fresh environment read")])
    wp.environment(project, run, evidence=document(run, "refresh.json", data))
    report = wp.status(project, run, packet="one")
    assert report["packet"]["status"] == "stale" and report["overall"] == "incomplete"


def test_definition_tamper_and_environment_contract_change_fail_closed(project, run):
    add(project, run, kind="probe")
    state = rs.load_run(project, run)
    state["environment"]["contract"]["target_level"] = "/Game/Other"
    (run / "run.json").write_text(json.dumps(state))
    with pytest.raises(rs.StateError, match="contract changed"):
        wp.status(project, run)


def test_status_resume_and_interrupted_running_packet_do_not_mutate(project, run):
    add(project, run, kind="probe")
    wp.start(project, run, packet="one")
    before = snapshot(run)
    report = wp.status(project, run, packet="one")
    result = subprocess.run([sys.executable, str(Path(wp.__file__)), "resume", "--project", str(project),
                             "--run", str(run), "--packet", "one"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout) == report
    assert report["packet"]["status"] == "running"
    assert report["tool_side_effects"] == "none"
    assert snapshot(run) == before


def test_interrupted_atomic_transition_keeps_prior_state_and_resume_does_not_replay(project, run, monkeypatch):
    add(project, run, kind="probe")
    wp.start(project, run, packet="one")
    source = document(run, "progress.json", progress_data(uncertainty=True))
    before = (run / "run.json").read_bytes()
    def fail_replace(*args):
        raise OSError("simulated interruption")
    monkeypatch.setattr(rs.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated interruption"):
        wp.progress(project, run, packet="one", evidence=source)
    assert (run / "run.json").read_bytes() == before
    assert wp.status(project, run)["packet"]["status"] == "running"


def test_lock_blocks_writes_and_resume_without_silent_repair(project, run):
    (run / ".run.lock").write_text("interrupted")
    before = snapshot(run)
    with pytest.raises(rs.StateError, match="interrupted"):
        wp.status(project, run)
    with pytest.raises(rs.StateError, match="interrupted"):
        add(project, run)
    # Creating a draft is outside the helper; the stale lock itself is preserved.
    assert (run / ".run.lock").read_text() == "interrupted"
    assert snapshot(run)["run.json"] == before["run.json"]


def test_cli_error_is_two_and_init_requires_target_level(project):
    result = subprocess.run([sys.executable, str(Path(wp.__file__)), "init", "--project", str(project),
                             "--task", "missing-level"], capture_output=True, text=True)
    assert result.returncode == 2
    assert "target-level" in result.stderr


def setup_data(run, **overrides):
    return {**progress_data(), "phase": "running", "proof": [proof(run, "setup.txt", "current target-level setup state")], **overrides}


def test_setup_failure_is_durable_and_compact_resume_includes_it(project, run):
    source = document(run, "setup.json", setup_data(run, phase="blocked", blocked_reason="No permitted map creation capability",
                                                  objects=[], next_action="Operator must create exact target map"))
    report = wp.setup_progress(project, run, evidence=source)
    assert report["setup"]["status"] == "blocked"
    assert report["setup"]["objects"] == []
    assert "Operator" in report["setup"]["next_action"]
    assert report["setup"]["pause_reason"] == "No permitted map creation capability"
    before = snapshot(run)
    assert wp.status(project, run) == report
    assert snapshot(run) == before
    assert report["environment"]["status"] == "unverified"


def test_setup_uncertainty_needs_explicit_evidence_backed_reconciliation(project, run):
    source = document(run, "setup.json", setup_data(run, uncertainty=True))
    report = wp.setup_progress(project, run, evidence=source)
    assert report["setup"]["status"] == "paused"
    with pytest.raises(rs.StateError, match="Reconcile uncertain setup"):
        verify_environment(project, run)
    with pytest.raises(rs.StateError, match="setup-reconcile"):
        wp.setup_progress(project, run, evidence=document(run, "setup.json", setup_data(run)))
    report = wp.setup_reconcile(project, run, evidence=reconciliation(run))
    assert report["setup"]["status"] == "running" and report["setup"]["uncertainty"] is False
    assert report["setup"]["metrics"]["tool_calls"] == 1
    assert verify_environment(project, run)["setup"]["status"] == "verified"


def test_setup_budget_does_not_silently_reset_and_extension_is_explicit(project, run):
    report = wp.setup_progress(project, run, evidence=document(run, "setup.json", setup_data(run, tool_calls=20)))
    assert report["setup"]["status"] == "paused"
    with pytest.raises(rs.StateError, match="Setup budget exhausted"):
        wp.setup_reconcile(project, run, evidence=reconciliation(run))
    report = wp.setup_reconcile(project, run, evidence=reconciliation(run, budget_extension={"tool_calls": 5, "minutes": 2}))
    assert report["setup"]["effective_budget"] == {"tool_calls": 25, "minutes": 7}
    assert report["setup"]["metrics"]["tool_calls"] == 20
    with pytest.raises(rs.StateError, match="may not decrease"):
        wp.setup_progress(project, run, evidence=document(run, "setup.json", setup_data(run)))


def test_setup_cannot_be_reentered_after_environment_binding(project, run):
    verify_environment(project, run)
    with pytest.raises(rs.StateError, match="already bound"):
        wp.setup_progress(project, run, evidence=document(run, "setup.json", setup_data(run)))
    with pytest.raises(rs.StateError, match="already bound"):
        wp.setup_reconcile(project, run, evidence=reconciliation(run))


@pytest.mark.parametrize("phase", ["paused", "blocked"])
def test_setup_progress_does_not_restart_paused_or_blocked_setup(project, run, phase):
    wp.setup_progress(project, run, evidence=document(run, "setup.json", setup_data(run, phase=phase, blocked_reason="Needs inspection")))
    report = wp.setup_progress(project, run, evidence=document(run, "setup.json", setup_data(run, tool_calls=2)))
    assert report["setup"]["status"] == phase
    assert report["setup"]["metrics"]["tool_calls"] == 2
    assert wp.setup_reconcile(project, run, evidence=reconciliation(run))["setup"]["status"] == "running"


def test_setup_status_does_not_recommend_proceeding_with_stale_environment(project, run):
    verify_environment(project, run)
    (run / "findings" / "environment.txt").write_text("changed environment")
    report = wp.status(project, run)
    assert report["environment"]["status"] == "unverified"
    assert report["setup"]["status"] == "stale"
    assert report["setup"]["next_action"] == "Reverify environment evidence before further work"


def test_custom_setup_budget_and_queue_discovery(project):
    report = wp.init(project, task="setup-budget", target_level="/Game/TestRoom", setup_tool_calls=7, setup_minutes=3)
    run = Path(report["run_dir"])
    assert report["setup"]["effective_budget"] == {"tool_calls": 7, "minutes": 3}
    add(project, run, "first", "probe")
    report = add(project, run, "followup", "probe")
    assert [item["id"] for item in report["queue"]] == ["first", "followup"]
    assert all(set(item) == {"id", "status", "outcome", "phase", "lane", "role"} for item in report["queue"])


def test_definition_snapshot_tampering_is_rejected(project, run):
    report = add(project, run, kind="probe")
    (run / report["packet"]["definition_ref"]["path"]).write_text("{}")
    with pytest.raises(rs.StateError, match="Evidence changed"):
        wp.status(project, run)
