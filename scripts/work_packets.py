"""Bounded, evidence-backed work packets. This helper never calls the editor.

All paths are explicit. Evidence is an operator/worker report, not an enforced
tool-call proxy. Resume is read-only and never repeats an unfinished operation.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import uuid

import run_state as rs

StateError = rs.StateError
WORKFLOW = "packets-v1"
STATUSES = {"pending", "running", "paused", "blocked", "completed"}
PHASES = ("pre-production", "production", "post-production")
ROLES = {"layout-artist", "gameplay-programmer", "ai-programmer", "environment-artist", "lighting-artist", "reviewer"}
PHASE_CHECKS = {
    "pre-production": {"playable-blockout", "core-loop", "art-direction"},
    "production": {"level-content", "ai-gameplay", "integrated-playthrough"},
    "post-production": {"lighting-materials", "smoke-qa"},
}


def _require(condition, message):
    if not condition:
        raise StateError(message)


def _text(value, label):
    _require(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty text")
    return value


def _number(value, label, *, positive=False, integer=False):
    _require(type(value) in ((int,) if integer else (int, float))
             and math.isfinite(value) and (value > 0 if positive else value >= 0),
             f"{label} must be a {'positive' if positive else 'nonnegative'} {'integer' if integer else 'number'}")
    return value


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _read_source(run, source):
    path = rs._inside(rs._absolute(source, "source"), run, "source")
    return rs._json(path)


def _file_ref(run, relative):
    path = rs._relative(run, relative, "evidence")
    _require(path.is_file() and path.stat().st_size > 0, f"Evidence must be a nonempty file: {relative}")
    return {"path": path.relative_to(run).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _verify_ref(run, ref):
    _require(isinstance(ref, dict), "Invalid evidence reference")
    current = _file_ref(run, ref.get("path"))
    _require(current["sha256"] == ref.get("sha256"), f"Evidence changed: {ref.get('path')}")


def _references(run, values):
    _require(isinstance(values, list) and values, "evidence/proof must list nonempty run-relative files")
    _require(all(isinstance(value, str) for value in values) and len(values) == len(set(values)), "Evidence paths must be unique strings")
    return [_file_ref(run, value) for value in values]


def _snapshot(run, data, refs=()):
    relative = f"packets/evidence/{uuid.uuid4().hex}/record.json"
    path = rs._relative(run, relative, "snapshot")
    path.parent.mkdir(parents=True, exist_ok=False)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    snapshot = {"document": _file_ref(run, relative), "files": list(refs)}
    snapshot["fingerprint"] = _digest({"data": data, "files": list(refs)})
    return snapshot


def _verify_snapshot(run, snapshot):
    _require(isinstance(snapshot, dict) and isinstance(snapshot.get("files"), list), "Invalid evidence snapshot")
    _verify_ref(run, snapshot.get("document"))
    data = rs._json(rs._relative(run, snapshot["document"]["path"], "snapshot"))
    for ref in snapshot["files"]:
        _verify_ref(run, ref)
    _require(snapshot.get("fingerprint") == _digest({"data": data, "files": snapshot["files"]}), "Evidence fingerprint does not match")
    return data


def _budget(data):
    _require(isinstance(data, dict), "budget must be an object")
    return {"tool_calls": _number(data.get("tool_calls"), "budget.tool_calls", positive=True, integer=True),
            "minutes": _number(data.get("minutes"), "budget.minutes", positive=True)}


def _spec(data):
    _require(isinstance(data, dict), "Packet spec must be an object")
    identifier = rs._identifier(data.get("id"), "packet id")
    phase, lane, role = data.get("phase", PHASES[0]), data.get("lane", "editor"), data.get("role", "gameplay-programmer")
    _require(phase in PHASES, "Unknown production phase")
    _require(lane in {"editor", "concept"}, "lane must be editor or concept")
    _require(role in ROLES, "Unknown discipline role")
    if lane == "concept":
        _require(role == "environment-artist", "Concept lane requires environment-artist")
    _require(data.get("kind") in {"probe", "change"}, "Packet kind must be probe or change")
    outcome = _text(data.get("outcome"), "outcome")
    dependencies = data.get("depends_on")
    _require(isinstance(dependencies, list), "depends_on must be a list")
    for dependency in dependencies:
        rs._identifier(dependency, "dependency id")
    _require(len(dependencies) == len(set(dependencies)) and identifier not in dependencies, "Duplicate or self dependency")
    changes = data.get("allowed_changes")
    _require(isinstance(changes, list), "allowed_changes must be a list")
    for change in changes:
        _text(change, "allowed change")
    _require(not changes if data["kind"] == "probe" else bool(changes), "Probe changes must be empty; change packets must declare allowed_changes")
    if lane == "concept":
        for change in changes:
            # File ownership only: concept workers have no editor permission.
            _require(re.fullmatch(r"concepts/" + re.escape(identifier) + r"/[A-Za-z0-9_./-]*", change)
                     and ".." not in Path(change).parts, "Concept outputs must be run-relative concepts/<packet-id>/ paths")
    checks = data.get("checks")
    _require(isinstance(checks, list) and checks, "At least one acceptance check is required")
    normalized = []
    for check in checks:
        _require(isinstance(check, dict), "Acceptance checks must be objects")
        kind = check.get("kind", "static")
        _require(kind in {"static", "runtime"}, "Check kind must be static or runtime")
        normalized.append({"id": rs._identifier(check.get("id"), "check id"),
                           "description": _text(check.get("description"), "check description"), "kind": kind})
    _require(len({check["id"] for check in normalized}) == len(normalized), "Duplicate acceptance check IDs")
    return {"id": identifier, "kind": data["kind"], "phase": phase, "lane": lane, "role": role, "outcome": outcome,
            "depends_on": dependencies, "allowed_changes": changes, "checks": normalized, "budget": _budget(data.get("budget"))}


def _metadata(run, state):
    _require(state.get("workflow") == WORKFLOW, "Not a packets-v1 run")
    pipeline = state.get("pipeline")
    _require(isinstance(pipeline, dict) and pipeline.get("phase") in PHASES
             and pipeline.get("status") in {"working", "awaiting_approval", "approved", "complete"},
             "Missing production pipeline state; start a new run for pre-pipeline previews")
    environment = state.get("environment")
    _require(isinstance(environment, dict), "Missing environment contract")
    contract = environment.get("contract")
    _require(isinstance(contract, dict) and environment.get("contract_sha256") == _digest(contract), "Environment contract changed; create a new run for a new target")
    _require(contract.get("project") == state["uproject"], "Environment project differs from run project")
    _require(isinstance(state.get("setup"), dict) and state["setup"].get("status") in {"pending", "running", "paused", "blocked", "verified"}, "Missing or invalid setup checkpoint")
    _budget(state["setup"].get("budget"))
    _require(isinstance(state.get("packets"), dict), "Missing packet map")
    specs = {}
    for identifier, packet in state["packets"].items():
        _require(isinstance(packet, dict) and packet.get("status") in STATUSES, "Invalid packet state")
        spec = _spec(_verify_snapshot(run, packet.get("definition")))
        _require(identifier == spec["id"], "Packet identity differs from immutable definition")
        specs[identifier] = spec
    visited, visiting = set(), set()
    def visit(identifier):
        _require(identifier in specs, f"Missing dependency: {identifier}")
        _require(identifier not in visiting, "Packet dependency cycle")
        if identifier in visited:
            return
        visiting.add(identifier)
        for dependency in specs[identifier]["depends_on"]:
            visit(dependency)
        visiting.remove(identifier)
        visited.add(identifier)
    for identifier in specs:
        visit(identifier)
    for lane in ("editor", "concept"):
        _require(sum(packet["status"] == "running" and specs[key]["lane"] == lane
                     for key, packet in state["packets"].items()) <= 1, "Multiple running packets in one lane")
    return specs


def _environment_fingerprint(run, state):
    environment = state["environment"]
    snapshot = environment.get("evidence")
    _require(snapshot is not None, "Environment is unverified")
    data = _verify_snapshot(run, snapshot)
    contract = environment["contract"]
    _require(data.get("observed_project") == contract["project"], "Observed project does not match selected .uproject")
    _require(data.get("observed_level") == contract["target_level"], "Observed level does not match exact target level")
    _require(data.get("persistence_verified") is True, "Environment persistence has not been verified")
    if contract["level_mode"] == "isolated":
        _require(data.get("level_created_for_run") is True, "Isolated level must be created for this run")
    return snapshot["fingerprint"]


def _observation_context(run, state, kind):
    if kind == "change":
        return _environment_fingerprint(run, state)
    try:
        return _environment_fingerprint(run, state)
    except (ValueError, OSError):
        # A read-only preflight probe may run without a verified editor binding.
        # Binding it still prevents reuse after environment setup/refresh.
        environment = state["environment"]
        evidence = environment.get("evidence")
        return "unverified:" + _digest({"contract": environment["contract_sha256"],
                                       "last_evidence": evidence["fingerprint"] if evidence else None})


def _current_result(run, state, specs, identifier, visiting=None):
    visiting = set() if visiting is None else visiting
    _require(identifier not in visiting, "Packet dependency cycle")
    visiting.add(identifier)
    packet = state["packets"][identifier]
    _require(packet["status"] == "completed", f"Dependency {identifier} is not completed")
    result = packet.get("result")
    _verify_snapshot(run, result)
    bindings = packet.get("result_bindings", {})
    context = "concept:" + state["environment"]["contract_sha256"] if specs[identifier]["lane"] == "concept" else _observation_context(run, state, specs[identifier]["kind"])
    _require(bindings.get("environment") == context,
             f"Packet {identifier} has stale environment evidence")
    for dependency in specs[identifier]["depends_on"]:
        fingerprint = _current_result(run, state, specs, dependency, visiting)
        _require(bindings.get("dependencies", {}).get(dependency) == fingerprint, f"Packet {identifier} has stale dependency {dependency}")
    visiting.remove(identifier)
    return result["fingerprint"]


def _bindings(run, state, specs, identifier):
    spec = specs[identifier]
    dependencies = {dependency: _current_result(run, state, specs, dependency) for dependency in spec["depends_on"]}
    environment = "concept:" + state["environment"]["contract_sha256"] if spec["lane"] == "concept" else _observation_context(run, state, spec["kind"])
    if spec["kind"] == "change" and spec["lane"] == "editor":
        _require(not any(key != identifier and packet.get("uncertainty") is True
                         and specs[key]["lane"] == "editor" for key, packet in state["packets"].items()), "Reconcile other uncertain writes before another change packet")
    return {"environment": environment, "dependencies": dependencies}


def _execution_phase(state, specs, identifier):
    _require(specs[identifier]["phase"] == state["pipeline"]["phase"] and state["pipeline"]["status"] != "complete",
             "Packet is outside the active production phase; obtain phase approval before advancing")


def _lane_available(state, specs, identifier):
    _require(not any(key != identifier and value["status"] == "running"
                     and specs[key]["lane"] == specs[identifier]["lane"] for key, value in state["packets"].items()),
             "Another packet is running in this lane")


def _limits(run, packet, spec):
    limits = dict(spec["budget"])
    for snapshot in packet.get("budget_extensions", []):
        extension = _budget(_verify_snapshot(run, snapshot)["budget_extension"])
        for key in limits:
            limits[key] += extension[key]
    return limits


def _metrics(data, previous):
    metrics = {"tool_calls": _number(data.get("tool_calls"), "tool_calls", integer=True),
               "elapsed_seconds": _number(data.get("elapsed_seconds"), "elapsed_seconds")}
    _require(all(metrics[key] >= previous[key] for key in metrics), "Cumulative metrics may not decrease")
    return metrics


def _at_budget(metrics, limits):
    return metrics["tool_calls"] >= limits["tool_calls"] or metrics["elapsed_seconds"] >= limits["minutes"] * 60


def _over_budget(metrics, limits):
    return metrics["tool_calls"] > limits["tool_calls"] or metrics["elapsed_seconds"] > limits["minutes"] * 60


def _packet(state, identifier):
    _require(identifier in state["packets"], f"Unknown packet: {identifier}")
    return state["packets"][identifier]


def _save(run, state):
    state["validation"] = {"status": "invalidated", "reason": "packet evidence changed", "updated_at": rs._now()}
    rs._atomic_json(run / "run.json", state)


@contextmanager
def _update(project, run_dir, config=None):
    with rs._update(project, run_dir, config) as (run, state):
        specs = _metadata(run, state)
        yield run, state, specs


def init(project, *, task, target_level, level_mode="isolated", existing_level_reason=None,
         config=None, plugin_revision=None, setup_tool_calls=20, setup_minutes=5):
    _require(isinstance(target_level, str) and re.fullmatch(r"/Game/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+", target_level),
             "target_level must be an exact /Game/... package path")
    _require(level_mode in {"isolated", "existing"}, "level_mode must be isolated or existing")
    if level_mode == "existing":
        _text(existing_level_reason, "existing_level_reason")
    else:
        _require(existing_level_reason is None, "existing_level_reason only applies to existing mode")
    setup_budget = _budget({"tool_calls": setup_tool_calls, "minutes": setup_minutes})
    state = rs.init_run(project, task=task, config=config, plugin_revision=plugin_revision)
    with rs._update(project, state["run_dir"], config) as (run, state):
        contract = {"project": state["uproject"], "target_level": target_level, "level_mode": level_mode,
                    "existing_level_reason": existing_level_reason}
        state.update(workflow=WORKFLOW, packets={}, pipeline={"phase": PHASES[0], "status": "working", "history": []},
                     environment={"contract": contract, "contract_sha256": _digest(contract), "evidence": None},
                     setup={"status": "pending", "budget": setup_budget, "metrics": {"tool_calls": 0, "elapsed_seconds": 0},
                            "uncertainty": False, "budget_extensions": []})
        _save(run, state)
    return status(project, state["run_dir"], config=config)


def environment(project, run_dir, *, evidence, config=None):
    with _update(project, run_dir, config) as (run, state, specs):
        _require(state["setup"].get("uncertainty") is not True, "Reconcile uncertain setup operations before environment verification")
        data = _read_source(run, evidence)
        contract = state["environment"]["contract"]
        _require(data.get("observed_project") == contract["project"], "Observed project does not match selected .uproject")
        _require(data.get("observed_level") == contract["target_level"], "Observed level does not match exact target level")
        _require(data.get("persistence_verified") is True, "Environment persistence has not been verified")
        if contract["level_mode"] == "isolated":
            _require(data.get("level_created_for_run") is True, "Isolated level must be created for this run")
        refs = _references(run, data.get("evidence"))
        previous = state["environment"].get("evidence")
        snapshot = _snapshot(run, data, refs)
        state["environment"]["evidence"] = snapshot
        state["setup"].update(status="verified", next_action="Proceed with a bounded packet")
        if previous is None or previous["fingerprint"] != snapshot["fingerprint"]:
            for identifier, packet in state["packets"].items():
                if packet["status"] == "running" and specs[identifier]["lane"] == "editor":
                    packet.update(status="paused", pause_reason="environment evidence changed")
        _save(run, state)
    return status(project, run_dir, config=config)


def setup_progress(project, run_dir, *, evidence, config=None):
    """Checkpoint authorized environment setup; never perform the setup itself."""
    with _update(project, run_dir, config) as (run, state, specs):
        _require(state["environment"].get("evidence") is None, "Environment is already bound; use normal packets for later changes")
        setup = state["setup"]
        data = _read_source(run, evidence)
        metrics = _metrics(data, setup["metrics"])
        _require(data.get("phase") in {"running", "paused", "blocked"}, "Setup phase must be running, paused, or blocked")
        _require(isinstance(data.get("objects"), list) and all(isinstance(item, str) for item in data["objects"]), "objects must be a string list")
        _require(type(data.get("uncertainty")) is bool, "uncertainty must be true or false")
        _require(not setup.get("uncertainty") or data["uncertainty"], "Use setup-reconcile to resolve uncertain setup operations")
        _text(data.get("next_action"), "next_action")
        if data["phase"] == "blocked":
            _text(data.get("blocked_reason"), "blocked_reason")
        refs = _references(run, data.get("proof"))
        phase = data["phase"]
        reason = data.get("blocked_reason")
        if data["uncertainty"]:
            phase, reason = "paused", "uncertain setup operation: reconcile before more writes"
        elif _at_budget(metrics, _limits(run, setup, setup)):
            phase, reason = "paused", "setup budget consumed: reconcile with additional budget"
        elif setup["status"] in {"paused", "blocked"} and phase == "running":
            phase, reason = setup["status"], setup.get("pause_reason") or "setup-reconcile required before more writes"
        setup.update(status=phase, metrics=metrics, uncertainty=data["uncertainty"], progress=_snapshot(run, data, refs),
                     objects=data["objects"], next_action=data["next_action"], pause_reason=reason)
        _save(run, state)
    return status(project, run_dir, config=config)


def setup_reconcile(project, run_dir, *, evidence, config=None):
    with _update(project, run_dir, config) as (run, state, specs):
        _require(state["environment"].get("evidence") is None, "Environment is already bound; use normal packets for later changes")
        setup = state["setup"]
        _require(setup["status"] != "pending", "No setup attempt to reconcile")
        data = _read_source(run, evidence)
        _text(data.get("reason"), "reconciliation reason")
        _text(data.get("next_action"), "next_action")
        _require(data.get("uncertainty") is False, "Reconciliation must resolve uncertainty explicitly")
        _require(isinstance(data.get("objects"), list) and all(isinstance(item, str) for item in data["objects"]), "objects must be a string list")
        refs = _references(run, data.get("proof"))
        limits = _limits(run, setup, setup)
        extension = data.get("budget_extension")
        if extension is not None:
            extension = _budget(extension)
            for key in limits:
                limits[key] += extension[key]
        _require(not _at_budget(setup["metrics"], limits), "Setup budget exhausted: provide sufficient budget_extension")
        snapshot = _snapshot(run, data, refs)
        if extension:
            setup["budget_extensions"].append(snapshot)
        setup.pop("progress", None)
        setup.pop("pause_reason", None)
        setup.update(status="running", uncertainty=False, reconciliation=snapshot,
                     objects=data["objects"], next_action=data["next_action"])
        _save(run, state)
    return status(project, run_dir, config=config)


def add(project, run_dir, *, spec, config=None):
    with _update(project, run_dir, config) as (run, state, specs):
        source = _read_source(run, spec)
        definition = _spec({"phase": state["pipeline"]["phase"], **source})
        _require(state["pipeline"]["status"] != "complete", "Pipeline is complete; start a new scoped run")
        _require(PHASES.index(definition["phase"]) >= PHASES.index(state["pipeline"]["phase"]), "Cannot add work to an earlier phase")
        identifier = definition["id"]
        _require(identifier not in state["packets"], "Packet IDs and definitions are immutable; add a new ID")
        _require(all(dependency in specs for dependency in definition["depends_on"]), "Dependencies must already be registered")
        _require(all(PHASES.index(specs[dependency]["phase"]) <= PHASES.index(definition["phase"])
                     for dependency in definition["depends_on"]), "Dependency cannot belong to a later phase")
        state["packets"][identifier] = {"status": "pending", "definition": _snapshot(run, definition),
                                         "metrics": {"tool_calls": 0, "elapsed_seconds": 0}, "uncertainty": False,
                                         "budget_extensions": []}
        _save(run, state)
    return status(project, run_dir, packet=identifier, config=config)


def start(project, run_dir, *, packet, config=None):
    with _update(project, run_dir, config) as (run, state, specs):
        _packet(state, packet)
        _execution_phase(state, specs, packet)
        current = _packet(state, packet)
        _require(current["status"] == "pending", "Only pending packets can start; use explicit reconcile for interrupted work")
        _lane_available(state, specs, packet)
        current.update(status="running", execution_bindings=_bindings(run, state, specs, packet), started_at=rs._now())
        _save(run, state)
    return status(project, run_dir, packet=packet, config=config)


def progress(project, run_dir, *, packet, evidence, config=None):
    with _update(project, run_dir, config) as (run, state, specs):
        current = _packet(state, packet)
        _execution_phase(state, specs, packet)
        _require(current["status"] == "running", "Progress requires a running packet")
        data = _read_source(run, evidence)
        metrics = _metrics(data, current["metrics"])
        _require(isinstance(data.get("objects"), list) and all(isinstance(item, str) for item in data["objects"]), "objects must be a string list")
        _require(type(data.get("uncertainty")) is bool, "uncertainty must be true or false")
        _text(data.get("next_action"), "next_action")
        current.update(metrics=metrics, uncertainty=data["uncertainty"], progress=_snapshot(run, data))
        reason = None
        try:
            _require(current.get("execution_bindings") == _bindings(run, state, specs, packet), "Environment/dependency changed")
        except (ValueError, OSError) as exc:
            reason = str(exc)
        if data["uncertainty"]:
            reason = "uncertain operation: reconcile before further work"
        elif _at_budget(metrics, _limits(run, current, specs[packet])):
            reason = "budget consumed: reconcile with additional budget or split remaining work"
        if reason:
            current.update(status="paused", pause_reason=reason)
        _save(run, state)
    return status(project, run_dir, packet=packet, config=config)


def reconcile(project, run_dir, *, packet, evidence, config=None):
    with _update(project, run_dir, config) as (run, state, specs):
        current = _packet(state, packet)
        _execution_phase(state, specs, packet)
        _require(current["status"] in {"running", "paused", "blocked", "completed"}, "Only interrupted or stale packets can be reconciled")
        if current["status"] == "completed":
            try:
                _current_result(run, state, specs, packet)
            except (ValueError, OSError):
                pass
            else:
                raise StateError("Completed current packet needs no reconciliation")
        _lane_available(state, specs, packet)
        data = _read_source(run, evidence)
        _text(data.get("reason"), "reconciliation reason")
        _text(data.get("next_action"), "next_action")
        _require(data.get("uncertainty") is False, "Reconciliation must resolve uncertainty explicitly")
        _require(isinstance(data.get("objects"), list) and all(isinstance(item, str) for item in data["objects"]), "objects must be a string list")
        refs = _references(run, data.get("proof"))
        bindings = _bindings(run, state, specs, packet)
        limits = _limits(run, current, specs[packet])
        extension = data.get("budget_extension")
        if extension is not None:
            extension = _budget(extension)
            for key in limits:
                limits[key] += extension[key]
        _require(not _at_budget(current["metrics"], limits), "Budget exhausted: provide sufficient explicit budget_extension or split work")
        snapshot = _snapshot(run, data, refs)
        if extension:
            current["budget_extensions"].append(snapshot)
        if current.get("result"):
            current.setdefault("previous_results", []).append(current.pop("result"))
            current.pop("result_bindings", None)
        current.pop("progress", None)
        current.pop("pause_reason", None)
        current.update(status="running", uncertainty=False, reconciliation=snapshot, execution_bindings=bindings)
        _save(run, state)
    return status(project, run_dir, packet=packet, config=config)


def finish(project, run_dir, *, packet, evidence, config=None):
    with _update(project, run_dir, config) as (run, state, specs):
        current = _packet(state, packet)
        _execution_phase(state, specs, packet)
        budget_pause = current["status"] == "paused" and current.get("pause_reason", "").startswith("budget consumed:")
        _require(current["status"] == "running" or budget_pause,
                 "Finish requires a running packet or budget-only pause; reconcile interrupted work first")
        _require(current.get("uncertainty") is not True, "Resolve uncertainty before finishing")
        bindings = _bindings(run, state, specs, packet)
        _require(current.get("execution_bindings") == bindings, "Environment/dependency changed; reconcile before finish")
        for key in ("progress", "reconciliation"):
            if current.get(key):
                _verify_snapshot(run, current[key])
        data = _read_source(run, evidence)
        metrics = _metrics(data, current["metrics"])
        if budget_pause:
            _require(metrics == current["metrics"] or data.get("no_new_engine_work") is True,
                     "Budget-paused finish permits already-gathered proof only; declare no_new_engine_work:true for finalization overhead")
        checks = data.get("checks")
        _require(isinstance(checks, list), "checks must be a list")
        expected = {check["id"]: check for check in specs[packet]["checks"]}
        supplied, refs = {}, []
        for check in checks:
            _require(isinstance(check, dict), "Check results must be objects")
            identifier = check.get("id")
            _require(isinstance(identifier, str) and identifier in expected and identifier not in supplied, "Unknown or duplicate acceptance check")
            _require(check.get("status") in {"pass", "fail"}, "Check status must be pass or fail")
            supplied[identifier] = check["status"]
            refs.append(_file_ref(run, check.get("evidence")))
        _require(set(supplied) == set(expected), "Every acceptance check needs a result")
        persistence = data.get("persistence")
        _require(isinstance(persistence, dict) and persistence.get("status") in {"verified", "not_applicable", "failed", "unknown"},
                 "persistence must declare verified, not_applicable, failed, or unknown")
        if specs[packet]["kind"] == "change":
            _require(persistence["status"] != "not_applicable", "Change packet requires verified persistence to complete; record failed/unknown otherwise")
        if persistence["status"] != "not_applicable":
            refs.append(_file_ref(run, persistence.get("evidence")))
        runtime = data.get("runtime", {"status": "not_run"})
        _require(isinstance(runtime, dict) and runtime.get("status") in {"not_run", "pass", "fail"}, "runtime status must be not_run, pass, or fail")
        if runtime["status"] != "not_run":
            refs.append(_file_ref(run, runtime.get("evidence")))
        if any(expected[key]["kind"] == "runtime" and value == "pass" for key, value in supplied.items()):
            _require(runtime["status"] == "pass", "Passing a runtime check requires runtime pass with actual evidence")
        data = {**data, "runtime": runtime}
        completed = (all(value == "pass" for value in supplied.values()) and runtime["status"] != "fail"
                     and persistence["status"] in {"verified", "not_applicable"})
        if specs[packet]["lane"] == "concept" and specs[packet]["kind"] == "change" and completed:
            outputs = _references(run, data.get("outputs"))
            allowed = specs[packet]["allowed_changes"]
            _require(all(any(ref["path"] == path or ref["path"].startswith(path.rstrip("/") + "/")
                             for path in allowed) for ref in outputs), "Concept outputs must match declared owned paths")
            refs.extend(outputs)
        current.update(status="completed" if completed else "blocked", metrics=metrics,
                       result=_snapshot(run, data, refs), result_bindings=bindings,
                       budget_exceeded=_over_budget(metrics, _limits(run, current, specs[packet])))
        _save(run, state)
    return status(project, run_dir, packet=packet, config=config)


def _phase_basis(run, state, specs):
    """Bind approval to the exact reviewed work, not a mutable narrative."""
    _environment_fingerprint(run, state)
    _require(state["setup"]["status"] == "verified" and not state["setup"].get("uncertainty"), "Setup must be verified")
    for key in ("progress", "reconciliation"):
        if state["setup"].get(key):
            _verify_snapshot(run, state["setup"][key])
    for identifier, packet in state["packets"].items():
        _require(packet["status"] != "running" and not packet.get("uncertainty"), "Settle all workers and uncertain writes before phase review")
        for key in ("progress", "reconciliation", "result"):
            if packet.get(key):
                _verify_snapshot(run, packet[key])
        _limits(run, packet, specs[identifier])
        if packet["status"] == "completed":
            _current_result(run, state, specs, identifier)
    return _digest({"phase": state["pipeline"]["phase"], "environment": state["environment"],
                    "setup": state["setup"], "packets": state["packets"]})


def phase_review(project, run_dir, *, evidence, config=None):
    with _update(project, run_dir, config) as (run, state, specs):
        pipeline = state["pipeline"]
        _require(pipeline["status"] != "complete", "Pipeline is complete")
        basis = _phase_basis(run, state, specs)
        data = _read_source(run, evidence)
        _text(data.get("summary"), "review summary")
        _require(data.get("phase") == pipeline["phase"], "Review must name the active phase")
        playable = data.get("playable")
        _require(isinstance(playable, dict) and playable.get("level") == state["environment"]["contract"]["target_level"],
                 "Every phase requires a playable handoff in the exact contracted level")
        for field in ("launch_instructions", "controls", "objectives"):
            _text(playable.get(field), "playable." + field)
        _require(isinstance(playable.get("known_issues"), list)
                 and all(isinstance(issue, str) and issue.strip() for issue in playable["known_issues"]),
                 "playable.known_issues must be an explicit list")
        _require(playable.get("runtime_status") == "pass", "Verify a playable runtime before phase review; static checks are insufficient")
        playable_ref = _file_ref(run, playable.get("runtime_evidence"))
        packets = {key: value for key, value in state["packets"].items() if specs[key]["phase"] == pipeline["phase"]}
        completed = {key for key, value in packets.items() if value["status"] == "completed"}
        _require(bool(completed), "A phase review requires at least one completed packet")
        included = data.get("included_packets")
        deferred = data.get("deferred_packets", {})
        _require(isinstance(included, list) and all(isinstance(key, str) for key in included)
                 and len(included) == len(set(included)) and set(included) == completed,
                 "Review must include every completed current-phase packet exactly once")
        _require(isinstance(deferred, dict) and set(deferred) == set(packets) - completed,
                 "Every unfinished current-phase packet needs an explicit deferral")
        for reason in deferred.values():
            _text(reason, "deferral reason")
        checks = data.get("checks")
        _require(isinstance(checks, list), "Phase checks must be a list")
        seen, refs = set(), [playable_ref]
        for check in checks:
            _require(isinstance(check, dict) and check.get("id") in PHASE_CHECKS[pipeline["phase"]]
                     and check["id"] not in seen, "Unknown or duplicate phase check")
            _require(check.get("status") in {"pass", "not_applicable"}, "Resolve failed phase criteria before approval")
            if check["status"] == "not_applicable":
                _text(check.get("reason"), "scope exclusion reason")
            seen.add(check["id"])
            refs.append(_file_ref(run, check.get("evidence")))
        _require(seen == PHASE_CHECKS[pipeline["phase"]], "Every phase criterion needs evidence or an explicit scope exclusion")
        review = _snapshot(run, {**data, "basis": basis}, refs)
        pipeline.update(status="awaiting_approval", review=review)
        pipeline.pop("approval", None)
        pipeline["history"].append({"event": "review", "phase": pipeline["phase"], "evidence": review})
        _save(run, state)
    return status(project, run_dir, config=config)


def _current_review(run, state, specs):
    review = state["pipeline"].get("review")
    _require(review is not None, "Create a phase review before requesting approval")
    data = _verify_snapshot(run, review)
    _require(data["basis"] == _phase_basis(run, state, specs), "Reviewed work changed; prepare a new phase review and obtain approval again")
    return review


def phase_approve(project, run_dir, *, evidence, config=None):
    with _update(project, run_dir, config) as (run, state, specs):
        _require(state["pipeline"]["status"] == "awaiting_approval", "Phase is not awaiting approval")
        review = _current_review(run, state, specs)
        data = _read_source(run, evidence)
        _require(data.get("decision") == "approved" and data.get("approved_by") == "user", "Explicit user approval is required")
        _require(data.get("review_fingerprint") == review["fingerprint"], "Approval must name the exact reviewed fingerprint")
        _text(data.get("user_message"), "actual user approval message")
        evaluation = data.get("human_evaluation")
        _require(isinstance(evaluation, dict) and evaluation.get("played") is True,
                 "Human play evaluation is required before approving every phase")
        _text(evaluation.get("feedback"), "human playtest feedback")
        refs = _references(run, data.get("proof"))
        refs.append(_file_ref(run, evaluation.get("evidence")))
        approval = _snapshot(run, data, refs)
        state["pipeline"].update(status="approved", approval=approval)
        state["pipeline"]["history"].append({"event": "approval", "phase": state["pipeline"]["phase"], "evidence": approval})
        _save(run, state)
    return status(project, run_dir, config=config)


def phase_advance(project, run_dir, *, config=None):
    with _update(project, run_dir, config) as (run, state, specs):
        pipeline = state["pipeline"]
        _require(pipeline["status"] == "approved", "Explicit user approval is required before advancing")
        review = _current_review(run, state, specs)
        approval = _verify_snapshot(run, pipeline.get("approval"))
        _require(approval.get("review_fingerprint") == review["fingerprint"] and approval.get("decision") == "approved"
                 and approval.get("approved_by") == "user", "Approval does not match this review")
        index = PHASES.index(pipeline["phase"])
        pipeline["history"].append({"event": "advance", "phase": pipeline["phase"], "review": review,
                                    "approval": pipeline["approval"], "at": rs._now()})
        if index == len(PHASES) - 1:
            pipeline["status"] = "complete"
        else:
            pipeline.update(phase=PHASES[index + 1], status="working")
            pipeline.pop("review", None)
            pipeline.pop("approval", None)
        _save(run, state)
    return status(project, run_dir, config=config)


def _phase_report(run, state, specs):
    pipeline = state["pipeline"]
    report = {key: pipeline[key] for key in ("phase", "status", "review", "approval") if key in pipeline}
    report["criteria"] = sorted(PHASE_CHECKS[pipeline["phase"]])
    if pipeline.get("review"):
        try:
            _current_review(run, state, specs)
            data = _verify_snapshot(run, pipeline["review"])
            report.update(summary=data["summary"], deferred_packets=data["deferred_packets"] if "deferred_packets" in data else {},
                          playable=data["playable"],
                          scope_exclusions=[check for check in data["checks"] if check["status"] == "not_applicable"])
            if pipeline.get("approval"):
                _verify_snapshot(run, pipeline["approval"])
        except (ValueError, OSError) as exc:
            report.update(status="stale", reason=str(exc))
    return report


def status(project, run_dir, *, packet=None, config=None):
    """Compact, read-only restoration packet. No inferred mission completion."""
    state = rs.load_run(project, run_dir, config)
    run = Path(state["run_dir"])
    specs = _metadata(run, state)
    environment_state = {**state["environment"]["contract"], "status": "verified"}
    try:
        environment_state["fingerprint"] = _environment_fingerprint(run, state)
    except (ValueError, OSError) as exc:
        environment_state.update(status="unverified", reason=str(exc))
    if state["environment"].get("evidence"):
        environment_state["evidence"] = state["environment"]["evidence"]
    setup = state["setup"]
    setup_report = {key: setup[key] for key in ("status", "metrics", "uncertainty", "pause_reason") if key in setup}
    try:
        setup_report["effective_budget"] = _limits(run, setup, setup)
        for key in ("reconciliation", "progress"):
            if setup.get(key):
                data = _verify_snapshot(run, setup[key])
                setup_report[key] = setup[key]
                setup_report.update(objects=data["objects"], next_action=data["next_action"])
        if setup["status"] == "verified":
            if environment_state["status"] == "verified":
                setup_report["next_action"] = "Proceed with a bounded packet"
            else:
                setup_report.update(status="stale", reason=environment_state.get("reason"),
                                    next_action="Reverify environment evidence before further work")
    except (ValueError, OSError) as exc:
        setup_report.update(status="stale", reason=str(exc))
    summaries = {}
    for identifier, current in state["packets"].items():
        summary = {"id": identifier, "status": current["status"], "outcome": specs[identifier]["outcome"],
                   "phase": specs[identifier]["phase"], "lane": specs[identifier]["lane"], "role": specs[identifier]["role"]}
        try:
            for key in ("progress", "reconciliation", "result"):
                if current.get(key):
                    _verify_snapshot(run, current[key])
            _limits(run, current, specs[identifier])
            if current["status"] == "completed":
                _current_result(run, state, specs, identifier)
            elif current["status"] == "running":
                _require(current.get("execution_bindings") == _bindings(run, state, specs, identifier), "Environment/dependency changed; reconcile before further work")
        except (ValueError, OSError) as exc:
            summary.update(status="stale", reason=str(exc))
        if current.get("result"):
            summary["result"] = current["result"]["document"]
        summaries[identifier] = summary
    if packet is not None:
        _packet(state, packet)
    else:
        candidates = [identifier for identifier, item in summaries.items()
                      if item["status"] != "completed" and item["phase"] == state["pipeline"]["phase"]]
        packet = next((key for key in candidates if summaries[key]["status"] == "running"), next(iter(candidates), None))
    selected = None
    if packet is not None:
        current = state["packets"][packet]
        selected = {**summaries[packet], "definition": specs[packet], "definition_ref": current["definition"]["document"],
                    "metrics": current["metrics"], "uncertainty": current.get("uncertainty", False),
                    "budget_exceeded": current.get("budget_exceeded", False),
                    "dependencies": [summaries[identifier] for identifier in specs[packet]["depends_on"]]}
        for key in ("progress", "reconciliation", "result", "pause_reason"):
            if current.get(key):
                selected[key] = current[key]
        # Inline the small restoration payload, while keeping full evidence on disk.
        for key in ("reconciliation", "progress", "result"):
            if current.get(key):
                try:
                    evidence = _verify_snapshot(run, current[key])
                    for field in ("objects", "next_action"):
                        if field in evidence:
                            selected[field] = evidence[field]
                except (ValueError, OSError):
                    pass  # Stale evidence is reported above; never present it as current.
        try:
            selected["effective_budget"] = _limits(run, current, specs[packet])
        except (ValueError, OSError):
            selected["effective_budget"] = None
    complete = bool(summaries) and all(item["status"] == "completed" for item in summaries.values())
    return {"workflow": WORKFLOW, "run_id": state["run_id"], "run_dir": str(run),
            "overall": "registered_packets_complete" if complete else "incomplete", "mission_status": "not_assessed",
            "packet_count": len(summaries), "completed_count": sum(item["status"] == "completed" for item in summaries.values()),
            "environment": environment_state, "setup": setup_report, "pipeline": _phase_report(run, state, specs),
            "queue": [{key: item[key] for key in ("id", "status", "outcome", "phase", "lane", "role")} for item in summaries.values()],
            "packet": selected, "tool_side_effects": "none"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "environment", "setup-progress", "setup-reconcile", "add", "start", "progress", "finish", "reconcile", "status", "resume", "phase-review", "phase-approve", "phase-advance"):
        sub = commands.add_parser(command)
        sub.add_argument("--project", required=True, help="Absolute project directory or .uproject")
        sub.add_argument("--config")
        if command == "init":
            sub.add_argument("--task", required=True)
            sub.add_argument("--target-level", required=True)
            sub.add_argument("--level-mode", choices=("isolated", "existing"), default="isolated")
            sub.add_argument("--existing-level-reason")
            sub.add_argument("--plugin-revision")
            sub.add_argument("--setup-tool-calls", type=int, default=20)
            sub.add_argument("--setup-minutes", type=float, default=5)
        else:
            sub.add_argument("--run", required=True)
        if command in {"start", "progress", "finish", "reconcile", "status", "resume"}:
            sub.add_argument("--packet", required=command not in {"status", "resume"})
        if command in {"environment", "setup-progress", "setup-reconcile", "progress", "finish", "reconcile", "phase-review", "phase-approve"}:
            sub.add_argument("--evidence", required=True)
        if command == "add":
            sub.add_argument("--spec", required=True)
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    if "run" in args:
        args["run_dir"] = args.pop("run")
    try:
        result = globals()["status" if command == "resume" else command.replace("-", "_")](**args)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
