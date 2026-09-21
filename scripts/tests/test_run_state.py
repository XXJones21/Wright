import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_state


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "Project"
    root.mkdir()
    (root / "Example.uproject").write_text("{}", encoding="utf-8")
    return root


def config(project, **settings):
    path = project / "wright" / "config.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(settings), encoding="utf-8")
    return path


def init(project):
    return run_state.init_run(project, task="test-task", plugin_revision="test-revision")


def snapshot(path):
    return {str(p.relative_to(path)): (p.stat().st_mtime_ns, p.read_bytes())
            for p in path.rglob("*") if p.is_file()}


def test_unique_runs_have_expected_schema_and_no_baseline_metrics(project):
    first, second = init(project), init(project)
    assert first["run_id"] != second["run_id"]
    assert first["schema_version"] == 1
    assert first["baseline"] == {"status": "pending"}
    assert first["validation"] == {"status": "pending"}
    assert first["plugin_revision"] == "test-revision"
    assert first["checkpoint"]["name"] == "initialized"
    assert all((Path(first["run_dir"]) / name).is_dir() for name in run_state.DIRECTORIES)
    assert Path(first["texture_staging"]).is_relative_to(project)


def test_project_must_be_explicit_absolute_and_exist(tmp_path):
    for value in (None, "relative", tmp_path / "missing"):
        with pytest.raises(run_state.StateError):
            init(value)
    with pytest.raises(run_state.StateError, match="exactly one"):
        init(tmp_path)


def test_ambiguous_project_requires_explicit_selection(project):
    second = project / "Other.uproject"
    second.write_text("{}")
    with pytest.raises(run_state.StateError, match="exactly one"):
        init(project)
    assert init(second)["uproject"] == str(second)
    selected = config(project, uproject="Example.uproject")
    assert run_state.init_run(config=selected, task="configured")["uproject"] == str(project / "Example.uproject")
    with pytest.raises(run_state.StateError, match="conflicts"):
        init(second)


@pytest.mark.parametrize("key", ["run_root", "texture_staging", "uproject"])
@pytest.mark.parametrize("value", ["../outside", "wright/../../outside", "C:\\outside", "/outside"])
def test_config_rejects_escape_before_writes(project, key, value):
    config(project, **{key: value})
    before = snapshot(project)
    with pytest.raises(run_state.StateError):
        init(project)
    assert snapshot(project) == before


def test_project_local_config_is_only_supported_location(project):
    elsewhere = project / "other.json"
    elsewhere.write_text("{}")
    with pytest.raises(run_state.StateError, match="Config must"):
        run_state.init_run(project, task="x", config=elsewhere)
    with pytest.raises(run_state.StateError, match="Explicit config"):
        run_state.init_run(config=project / "wright" / "config.json", task="x")


def test_relative_config_paths_and_config_only_resume(project):
    cfg = config(project, run_root="saved/runs", texture_staging="saved/textures")
    state = run_state.init_run(config=cfg, task="config-only")
    assert Path(state["run_root"]) == project / "saved" / "runs"
    assert run_state.load_run(None, state["run_dir"], cfg) == state


def test_resume_and_status_are_read_only_and_do_not_reinitialize(project):
    state = init(project)
    before = snapshot(project)
    assert run_state.load_run(project, state["run_dir"]) == state
    script = Path(run_state.__file__)
    for command in ("resume", "status"):
        result = subprocess.run([sys.executable, str(script), command, "--project", str(project),
                                 "--run", state["run_dir"]], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout
        assert json.loads(result.stdout) == state
    assert snapshot(project) == before
    missing = Path(state["run_dir"]) / "run.json"
    missing.unlink()
    before = snapshot(project)
    with pytest.raises(run_state.StateError, match="Cannot read"):
        run_state.load_run(project, state["run_dir"])
    assert snapshot(project) == before


def test_other_project_and_outside_run_rejected(project, tmp_path):
    state = init(project)
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(run_state.StateError, match="inside"):
        run_state.checkpoint(project, outside, name="planning")
    assert list(outside.iterdir()) == []
    state_path = Path(state["run_dir"]) / "run.json"
    state["project_root"] = str(outside)
    state_path.write_text(json.dumps(state))
    with pytest.raises(run_state.StateError, match="project_root"):
        run_state.load_run(project, state["run_dir"])


def test_artifact_revisions_preserve_history_and_invalidate_validation(project):
    state = init(project)
    source = project / "artifact.md"
    source.write_text("first")
    first = run_state.register_artifact(project, state["run_dir"], task_id="T1", source=source)
    old = first["artifacts"][source.name]
    source.write_text("second")
    second = run_state.register_artifact(project, state["run_dir"], task_id="T1", source=source)
    new = second["artifacts"][source.name]
    assert old["revision"] == 1 and new["revision"] == 2
    assert old["path"] != new["path"] and old["sha256"] != new["sha256"]
    assert (Path(state["run_dir"]) / old["path"]).read_text() == "first"
    assert (Path(state["run_dir"]) / new["path"]).read_text() == "second"
    assert second["validation"]["status"] == "invalidated"
    assert second["baseline"] == {"status": "pending"}
    assert run_state.load_run(project, state["run_dir"]) == second
    assert not list((Path(state["run_dir"]) / "artifacts").glob("*.md"))
    with pytest.raises(run_state.StateError, match="another task"):
        run_state.register_artifact(project, state["run_dir"], task_id="T2", source=source)


def test_artifact_binds_current_synthesis_and_reregistration_refreshes_binding(project):
    state = init(project)
    run = Path(state["run_dir"])
    plan = run / "plan.md"
    first_plan = "## Synthesis (design)\n\nBUILD TASKS\n- [editor] Original: first task\n"
    plan.write_text(first_plan, encoding="utf-8")
    source = run / "findings" / "artifact.md"
    source.write_text("artifact remains unchanged", encoding="utf-8")
    state = run_state.register_artifact(project, run, task_id="01", source=source)
    first = state["artifacts"][source.name]
    assert first["synthesis_sha256"] == run_state.synthesis_hash(first_plan)
    revised_plan = first_plan.replace("Original: first task", "Revised: changed task")
    plan.write_text(revised_plan, encoding="utf-8")
    # Reading/resuming never rebinds stale evidence to a changed task definition.
    assert run_state.load_run(project, run)["artifacts"][source.name] == first
    state = run_state.register_artifact(project, run, task_id="01", source=source)
    second = state["artifacts"][source.name]
    assert second["synthesis_sha256"] == run_state.synthesis_hash(revised_plan)
    assert second["synthesis_sha256"] != first["synthesis_sha256"]
    assert second["sha256"] == first["sha256"]
    assert second["revision"] == first["revision"] + 1


def test_synthesis_hash_ignores_outer_space_and_fenced_headings():
    assert run_state.synthesis_hash("## Plan\nhello") is None
    assert run_state.synthesis_hash("## Synthesis\n\ntext\n\n") == run_state.synthesis_hash("## Synthesis (design)\ntext\n")
    assert run_state.synthesis_hash("## Synthesis\n```md\n## Synthesis\n```\n")
    assert run_state.synthesis_hash("## Synthesis (orchestrator)\ntext") == run_state.synthesis_hash("## Synthesis\ntext")
    assert run_state.synthesis_hash("## Synthesis (unsupported)\ntext") is None
    with pytest.raises(run_state.StateError, match="duplicates"):
        run_state.synthesis_hash("## Synthesis\nfirst\n## Synthesis (design)\nsecond\n")
    with pytest.raises(run_state.StateError, match="unclosed Markdown fence"):
        run_state.synthesis_hash("## Synthesis\n```md\nunfinished")


def test_duplicate_synthesis_prevents_registration_without_writes(project):
    state = init(project)
    run = Path(state["run_dir"])
    (run / "plan.md").write_text("## Synthesis\nfirst\n## Synthesis (design)\nsecond\n")
    source = run / "findings" / "artifact.md"
    source.write_text("content")
    before = snapshot(project)
    with pytest.raises(run_state.StateError, match="duplicates"):
        run_state.register_artifact(project, run, task_id="01", source=source)
    assert snapshot(project) == before


def test_artifact_missing_modified_or_outside_rejected(project, tmp_path):
    state = init(project)
    source = project / "artifact.md"
    with pytest.raises(run_state.StateError, match="does not exist"):
        run_state.register_artifact(project, state["run_dir"], task_id="T1", source=source)
    outside = tmp_path / "outside.md"
    outside.write_text("outside")
    with pytest.raises(run_state.StateError, match="inside"):
        run_state.register_artifact(project, state["run_dir"], task_id="T1", source=outside)
    source.write_text("content")
    state = run_state.register_artifact(project, state["run_dir"], task_id="T1", source=source)
    target = Path(state["run_dir"]) / state["artifacts"][source.name]["path"]
    target.write_text("tampered")
    with pytest.raises(run_state.StateError, match="modified artifact"):
        run_state.load_run(project, state["run_dir"])


def test_checkpoint_never_marks_runtime_or_validation_passed(project):
    state = init(project)
    changed = run_state.checkpoint(project, state["run_dir"], name="complete")
    assert changed["checkpoint"]["name"] == "complete"
    assert changed["validation"] == {"status": "pending"}
    assert changed["baseline"] == {"status": "pending"}
    with pytest.raises(run_state.StateError, match="Checkpoint"):
        run_state.checkpoint(project, state["run_dir"], name="runtime-passed")


def test_interrupted_atomic_update_keeps_previous_manifest(project, monkeypatch):
    state = init(project)
    run = Path(state["run_dir"])
    before = (run / "run.json").read_bytes()
    def fail_replace(*args):
        raise OSError("simulated interruption")
    monkeypatch.setattr(run_state.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        run_state.checkpoint(project, run, name="planning")
    assert (run / "run.json").read_bytes() == before
    assert not list(run.glob(".run-*.tmp"))
    assert run_state.load_run(project, run) == state


def test_interrupted_registration_does_not_select_or_replay_orphan(project, monkeypatch):
    state = init(project)
    source = project / "artifact.md"
    source.write_text("first")
    state = run_state.register_artifact(project, state["run_dir"], task_id="T1", source=source)
    source.write_text("second")
    def fail_replace(*args):
        raise OSError("simulated interruption")
    monkeypatch.setattr(run_state.os, "replace", fail_replace)
    with pytest.raises(OSError):
        run_state.register_artifact(project, state["run_dir"], task_id="T1", source=source)
    before = snapshot(project)
    assert run_state.load_run(project, state["run_dir"]) == state
    assert snapshot(project) == before
    assert len(list((Path(state["run_dir"]) / "artifacts").rglob("*.md"))) == 2


def test_stale_lock_fails_closed_without_repair(project):
    state = init(project)
    lock = Path(state["run_dir"]) / ".run.lock"
    lock.write_text("interrupted")
    before = snapshot(project)
    with pytest.raises(run_state.StateError, match="interrupted"):
        run_state.load_run(project, state["run_dir"])
    with pytest.raises(run_state.StateError, match="interrupted"):
        run_state.checkpoint(project, state["run_dir"], name="planning")
    assert snapshot(project) == before


@pytest.mark.parametrize("key,value", [("run_id", "other"), ("run_dir", "/other"),
                                       ("schema_version", 2), ("plugin_revision", "")])
def test_invalid_run_identity_is_read_only_failure(project, key, value):
    state = init(project)
    state[key] = value
    run = next((project / "wright" / "runs").iterdir())
    (run / "run.json").write_text(json.dumps(state))
    before = snapshot(project)
    with pytest.raises(run_state.StateError):
        run_state.load_run(project, run)
    assert snapshot(project) == before


@pytest.mark.parametrize("key,value", [("path", "../../artifact.md"), ("revision", 12),
                                       ("task_id", "other"), ("sha256", "incorrect")])
def test_invalid_artifact_metadata_is_read_only_failure(project, key, value):
    state = init(project)
    source = project / "artifact.md"
    source.write_text("content")
    state = run_state.register_artifact(project, state["run_dir"], task_id="T1", source=source)
    state["artifacts"][source.name][key] = value
    run = Path(state["run_dir"])
    (run / "run.json").write_text(json.dumps(state))
    before = snapshot(project)
    with pytest.raises(run_state.StateError):
        run_state.load_run(project, run)
    assert snapshot(project) == before


def test_symlink_escape_rejected_when_supported(project, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (project / "wright").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is unavailable on this host")
    with pytest.raises(run_state.StateError, match="inside"):
        init(project)
    assert list(outside.iterdir()) == []
