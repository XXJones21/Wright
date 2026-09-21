"""Explicit project-local run state. No editor calls, network, or replay.

Run ``python scripts/run_state.py --help`` for the small CLI. ``resume`` is a
read-only integrity check; a successful response never executes pending work.
The artifact map contains current immutable revisions. Plan.md is narrative and
must link the exact current ``artifacts[name]["path"]`` after registration.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import subprocess
import tempfile
import uuid

SCHEMA_VERSION = 1
DIRECTORIES = ("findings", "artifacts", "captures", "plates", "toolapi")
CHECKPOINTS = ("initialized", "planning", "review", "ready", "executing", "verification", "complete", "blocked")


class StateError(ValueError):
    """Invalid, missing, or interrupted state; requires explicit correction."""


def _absolute(value: str | Path, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise StateError(f"{label} must be an absolute path")
    return path.resolve()


def _inside(path: Path, root: Path, label: str) -> Path:
    path = path.resolve()
    if path == root or not path.is_relative_to(root):
        raise StateError(f"{label} must be inside {root}")
    return path


def _relative(root: Path, value: str, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise StateError(f"{label} must be a nonempty relative path")
    path = Path(value)
    windows = PureWindowsPath(value)
    if path.is_absolute() or windows.drive or windows.root or ".." in windows.parts or ".." in path.parts:
        raise StateError(f"{label} must be relative without traversal")
    return _inside(root / path, root, label)


def _json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StateError(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise StateError(f"Expected JSON object: {path}")
    return data


def resolve_project(project: str | Path | None = None, config: str | Path | None = None) -> dict:
    """Resolve an explicitly chosen project, never the cwd or a global default."""
    config_path = _absolute(config, "config") if config is not None else None
    if project is None:
        if config_path is None or config_path.name != "config.json" or config_path.parent.name != "wright":
            raise StateError("Pass --project or an explicit <project>/wright/config.json")
        root = config_path.parent.parent
        chosen = None
    else:
        chosen = _absolute(project, "project")
        root = chosen.parent if chosen.suffix.lower() == ".uproject" else chosen
        chosen = chosen if chosen.suffix.lower() == ".uproject" else None
    if not root.is_dir():
        raise StateError(f"Project directory does not exist: {root}")
    expected = _inside(root / "wright" / "config.json", root, "config")
    if config_path is not None and config_path != expected:
        raise StateError("Config must be <project>/wright/config.json")
    config_path = config_path or expected
    settings = _json(config_path) if config_path.exists() else {}
    if config is not None and not config_path.is_file():
        raise StateError(f"Explicit config does not exist: {config_path}")
    if settings.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        raise StateError("Unsupported project config schema_version")
    configured = settings.get("uproject")
    if configured is not None:
        configured = _relative(root, configured, "uproject")
        if chosen is not None and chosen != configured:
            raise StateError("Explicit .uproject conflicts with project config")
        chosen = configured
    if chosen is None:
        candidates = list(root.glob("*.uproject"))
        if len(candidates) != 1:
            raise StateError("Project must contain exactly one .uproject, or select one explicitly")
        chosen = candidates[0].resolve()
    _inside(chosen, root, "uproject")
    if chosen.suffix.lower() != ".uproject" or not chosen.is_file():
        raise StateError(f"Selected .uproject does not exist: {chosen}")
    return {
        "project_root": root, "uproject": chosen,
        "run_root": _relative(root, settings.get("run_root", "wright/runs"), "run_root"),
        "texture_staging": _relative(root, settings.get("texture_staging", "wright/textures"), "texture_staging"),
    }


def _atomic_json(path: Path, state: dict) -> None:
    """Same-directory replace keeps the previous manifest intact on interruption."""
    fd, temporary = tempfile.mkstemp(prefix=".run-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(state, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _revision() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1],
                              capture_output=True, text=True, check=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", value) or value.endswith("."):
        raise StateError(f"Invalid {label}: use 1-80 letters, digits, dots, underscores or hyphens")
    if value.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        raise StateError(f"Reserved filesystem name for {label}")
    return value


def synthesis_hash(plan_text: str) -> str | None:
    """Bind evidence to the authoritative Synthesis body, excluding outer space."""
    from plan_sections import split_sections
    try:
        parsed = split_sections(plan_text)
    except ValueError as exc:
        raise StateError(f"Invalid plan sections: {exc}") from exc
    sections = [body for title, body in parsed
                if title in {"Synthesis", "Synthesis (design)", "Synthesis (orchestrator)"}]
    if len(sections) > 1:
        raise StateError("Expected exactly one Synthesis section, found duplicates")
    return hashlib.sha256(sections[0].strip().encode("utf-8")).hexdigest() if sections else None


def init_run(project: str | Path | None = None, *, task: str,
             config: str | Path | None = None, plugin_revision: str | None = None) -> dict:
    paths = resolve_project(project, config)
    slug = _identifier(task, "task")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + slug + "-" + uuid.uuid4().hex
    run = _inside(paths["run_root"] / run_id, paths["project_root"], "run")
    run.mkdir(parents=True, exist_ok=False)
    for name in DIRECTORIES:
        (run / name).mkdir()
    paths["texture_staging"].mkdir(parents=True, exist_ok=True)
    state = {
        "schema_version": SCHEMA_VERSION, "run_id": run_id, "task": slug,
        **{key: str(value) for key, value in paths.items()}, "run_dir": str(run),
        "plugin_revision": plugin_revision or _revision(), "created_at": _now(),
        "checkpoint": {"name": "initialized", "updated_at": _now()},
        "baseline": {"status": "pending"}, "validation": {"status": "pending"},
        "artifacts": {},
    }
    _atomic_json(run / "run.json", state)
    return state


def _load(paths: dict, run: Path) -> dict:
    state_file = _inside(run / "run.json", run, "run.json")
    state = _json(state_file)
    if state.get("schema_version") != SCHEMA_VERSION:
        raise StateError("Unsupported run schema_version")
    if state.get("run_id") != run.name or state.get("run_dir") != str(run):
        raise StateError("Run identity does not match directory")
    for key, value in paths.items():
        if state.get(key) != str(value):
            raise StateError(f"Run {key} does not match selected project/config")
    if not isinstance(state.get("checkpoint"), dict) or state["checkpoint"].get("name") not in CHECKPOINTS:
        raise StateError("Invalid checkpoint")
    if not isinstance(state.get("plugin_revision"), str) or not state["plugin_revision"]:
        raise StateError("Missing plugin revision")
    for name in DIRECTORIES:
        directory = _inside(run / name, run, name)
        if not directory.is_dir():
            raise StateError(f"Missing run directory: {name}")
    artifacts = state.get("artifacts")
    if not isinstance(artifacts, dict):
        raise StateError("Invalid artifact map")
    for name, record in artifacts.items():
        _identifier(name, "artifact name")
        if not isinstance(record, dict):
            raise StateError(f"Invalid artifact record: {name}")
        _identifier(record.get("task_id"), "task_id")
        if type(record.get("revision")) is not int or record["revision"] < 1:
            raise StateError(f"Invalid artifact revision: {name}")
        artifact = _relative(run, record.get("path"), "artifact")
        revisions = _inside(run / "artifacts" / "revisions", run, "revisions")
        _inside(artifact, revisions, "artifact revision")
        expected_parent = revisions / record["task_id"]
        _inside(artifact, expected_parent, "task artifact")
        if artifact.name != name or not re.fullmatch(rf"{record['revision']}-[0-9a-f]{{32}}", artifact.parent.name):
            raise StateError(f"Artifact path does not match name/revision: {name}")
        if not artifact.is_file() or hashlib.sha256(artifact.read_bytes()).hexdigest() != record.get("sha256"):
            raise StateError(f"Missing or modified artifact: {name}")
    return state


def _run_path(paths: dict, run_dir: str | Path) -> Path:
    run = _inside(_absolute(run_dir, "run"), paths["run_root"], "run")
    if not run.is_dir():
        raise StateError(f"Run does not exist: {run}")
    _inside(run / ".run.lock", run, "run lock")
    return run


def load_run(project: str | Path | None, run_dir: str | Path,
             config: str | Path | None = None) -> dict:
    """Read-only status/resume; fail closed on missing state or active/stale lock."""
    paths = resolve_project(project, config)
    run = _run_path(paths, run_dir)
    if (run / ".run.lock").exists():
        raise StateError("Run update is active or interrupted; inspect .run.lock before proceeding")
    state = _load(paths, run)
    if (run / ".run.lock").exists():
        raise StateError("Run changed during read; retry after update completes")
    return state


@contextmanager
def _update(project, run_dir, config):
    paths = resolve_project(project, config)
    run = _run_path(paths, run_dir)
    lock = run / ".run.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise StateError("Run update is active or interrupted; inspect .run.lock before proceeding") from exc
    try:
        os.close(fd)
        yield run, _load(paths, run)
    finally:
        lock.unlink()


def register_artifact(project: str | Path | None, run_dir: str | Path, *, task_id: str,
                      source: str | Path, name: str | None = None,
                      config: str | Path | None = None) -> dict:
    """Publish a new immutable revision and atomically switch the current pointer.

    An interrupted manifest update can leave an unreferenced revision. It is never
    replayed or selected automatically; the prior current revision stays valid.
    Re-registering after a Synthesis change requires conductor reconciliation first.
    """
    paths = resolve_project(project, config)
    source_path = _inside(_absolute(source, "source"), paths["project_root"], "source")
    if not source_path.is_file():
        raise StateError(f"Artifact source does not exist: {source_path}")
    task_id = _identifier(task_id, "task_id")
    name = _identifier(name or source_path.name, "artifact name")
    content = source_path.read_bytes()
    with _update(project, run_dir, config) as (run, state):
        if state.get("workflow") == "packets-v1":
            raise StateError("Packet runs use work_packets finish, not legacy artifact registration")
        plan_path = _inside(run / "plan.md", run, "plan")
        synthesis_sha256 = synthesis_hash(plan_path.read_text(encoding="utf-8") if plan_path.exists() else "")
        previous = state["artifacts"].get(name)
        if previous and previous["task_id"] != task_id:
            raise StateError("Artifact name belongs to another task")
        revision = previous["revision"] + 1 if previous else 1
        relative = f"artifacts/revisions/{task_id}/{revision}-{uuid.uuid4().hex}/{name}"
        target = _relative(run, relative, "artifact revision")
        target.parent.mkdir(parents=True, exist_ok=False)
        with target.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        record = {"task_id": task_id, "revision": revision, "path": relative,
                  "sha256": hashlib.sha256(content).hexdigest(), "synthesis_sha256": synthesis_sha256}
        state["artifacts"][name] = record
        state["validation"] = {"status": "invalidated", "reason": "artifact revision changed", "updated_at": _now()}
        _atomic_json(run / "run.json", state)
    return state


def checkpoint(project: str | Path | None, run_dir: str | Path, *, name: str,
               config: str | Path | None = None) -> dict:
    """Record an operator checkpoint, never a validation or runtime success claim."""
    if name not in CHECKPOINTS:
        raise StateError(f"Checkpoint must be one of: {', '.join(CHECKPOINTS)}")
    with _update(project, run_dir, config) as (run, state):
        if state.get("workflow") == "packets-v1":
            raise StateError("Packet runs use work_packets transitions, not legacy checkpoints")
        state["checkpoint"] = {"name": name, "updated_at": _now()}
        _atomic_json(run / "run.json", state)
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "status", "resume", "checkpoint", "register"):
        sub = commands.add_parser(command)
        sub.add_argument("--project", help="Absolute project directory or explicitly selected .uproject")
        sub.add_argument("--config", help="Explicit absolute <project>/wright/config.json")
        if command == "init":
            sub.add_argument("--task", required=True)
            sub.add_argument("--plugin-revision")
        else:
            sub.add_argument("--run", required=True, help="Absolute existing run directory")
        if command == "checkpoint":
            sub.add_argument("--name", required=True, choices=CHECKPOINTS)
        if command == "register":
            sub.add_argument("--task", required=True)
            sub.add_argument("--source", required=True)
            sub.add_argument("--name")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            state = init_run(args.project, task=args.task, config=args.config, plugin_revision=args.plugin_revision)
        elif args.command in ("status", "resume"):
            state = load_run(args.project, args.run, args.config)
        elif args.command == "checkpoint":
            state = checkpoint(args.project, args.run, name=args.name, config=args.config)
        else:
            state = register_artifact(args.project, args.run, task_id=args.task, source=args.source, name=args.name, config=args.config)
        print(json.dumps(state, indent=2, sort_keys=True))
        return 0
    except (StateError, OSError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
