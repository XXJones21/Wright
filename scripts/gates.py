"""Deterministic gates for a Wright run. Pure Python, no model, no network.

Ported from Valar's wright_plan.py (grounding gate, claim/verdict parsers) and
extended with lane tags on build tasks and a tool-call gate (see part 2).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LANES = ("editor", "blueprint", "texture", "needs-you")

_CLM_LINE = re.compile(
    r"^[ \t>*_`-]*`?(CLM[ _-]?\d+)`?[ \t:.)\]\-]*(.*?)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
_VERDICT = re.compile(r"\b(VERIFIED|REJECTED|UNVERIFIABLE)\b", re.IGNORECASE)
_CAMEL = re.compile(r"\b([A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+)\b")
_SNAKE = re.compile(r"\b([A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+)\b")
_SPAN = re.compile(r"[`\"'“]([^`\"'”\n]{2,48})[`\"'”]")
_LANE = re.compile(r"^\[(editor|blueprint|texture|needs-you)\]\s*", re.IGNORECASE)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def _clm_id(raw: str) -> str | None:
    m = re.search(r"\d+", raw or "")
    return f"CLM-{int(m.group(0))}" if m else None


def parse_clm_claims(plan_beat_text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _CLM_LINE.finditer(plan_beat_text or ""):
        cid = _clm_id(m.group(1))
        body = (m.group(2) or "").strip()
        if cid and body and cid not in out:
            out[cid] = body
    return out


def parse_clm_verdicts(investigator_text: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for m in _CLM_LINE.finditer(investigator_text or ""):
        cid = _clm_id(m.group(1))
        if not cid or cid in seen:
            continue
        v = _VERDICT.search(m.group(2) or "")
        if not v:
            continue
        seen.add(cid)
        out.append({"id": cid, "verdict": v.group(1).upper(), "line": m.group(0).strip()})
    return out


def extract_symbols(text: str) -> set[str]:
    syms: set[str] = set()
    for rx in (_CAMEL, _SNAKE):
        syms.update(m.group(1) for m in rx.finditer(text or ""))
    for m in _SPAN.finditer(text or ""):
        s = m.group(1).strip()
        if 2 <= len(s) <= 48:
            syms.add(s)
    return syms


def grounding_gate(rejected_claim_texts: list[str], artifacts: list[tuple[str, str]],
                   gps_text: str = "") -> list[dict]:
    """A symbol named in a REJECTED claim and absent from the GPS is forbidden;
    return every (artifact, symbol) where a forbidden symbol appears."""
    grounded_symbols = {_norm(s) for s in extract_symbols(gps_text)}
    grounded_symbols.update(_norm(s) for s in re.findall(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", gps_text))
    forbidden: dict[str, str] = {}
    for claim in rejected_claim_texts:
        for s in extract_symbols(claim):
            ns = _norm(s)
            if len(ns) < 6:
                continue
            if ns not in grounded_symbols:
                forbidden.setdefault(ns, s)
    flags: list[dict] = []
    for title, content in artifacts:
        cn = _norm(content)
        for ns, orig in forbidden.items():
            if ns in cn:
                flags.append({"artifact": title, "symbol": orig})
    return flags


def parse_build_tasks(synthesis: str, cap: int = 8) -> list[dict]:
    """Lines under a BUILD TASKS heading: `- [lane] <title>: <brief>`.
    Lane defaults to editor. Stops at the first non-list line."""
    tasks: list[dict] = []
    in_block = False
    for ln in (synthesis or "").splitlines():
        s = ln.strip()
        if not in_block:
            if re.match(r"^#*\s*BUILD\s+TASKS\b", s, re.IGNORECASE):
                in_block = True
            continue
        if not s:
            continue
        m = re.match(r"^[-*\d.)\s]+(.+)$", s)
        if not m:
            break
        item = m.group(1).strip()
        lane = "editor"
        lm = _LANE.match(item)
        if lm:
            lane = lm.group(1).lower()
            item = item[lm.end():]
        title, _, brief = item.partition(":")
        tasks.append({"title": title.strip(), "brief": brief.strip() or title.strip(), "lane": lane})
        if len(tasks) >= cap:
            break
    return tasks


_FENCE = re.compile(r"```([^\n]*)\n(.*?)```", re.DOTALL)


def _sections(text: str, heading: str) -> list[str]:
    """Authoritative H2 sections; headings inside fences are not headings."""
    from plan_sections import split_sections
    try:
        sections = split_sections(text)
    except ValueError:
        return []  # Broken fences cannot establish authoritative sections.
    aliases = {
        "Plan": {"Plan", "Plan (orchestrator)"},
        "Synthesis": {"Synthesis", "Synthesis (design)", "Synthesis (orchestrator)"},
    }
    allowed = aliases.get(heading, {heading})
    return [body for title, body in sections if title in allowed]


def _section(plan_text: str, heading_prefix: str) -> str:
    sections = _sections(plan_text, heading_prefix)
    return sections[0] if len(sections) == 1 else ""


def _prose(text: str) -> str:
    """Remove fenced examples before recognizing control declarations/claim rows."""
    lines = []
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^[ \t]*(`{3,}|~{3,})(.*)$", line)
        if marker:
            token, tail = marker.groups()
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not tail.strip():
                fence = None
            lines.append("")
        elif fence is None:
            lines.append(line)
        else:
            lines.append("")
    return "\n".join(lines)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _json(body: str):
    def invalid_constant(value):
        raise ValueError(f"invalid JSON constant: {value}")
    return json.loads(body, object_pairs_hook=_unique_object, parse_constant=invalid_constant)


def parse_tool_api(plan_text: str, diagnostics: list[str] | None = None) -> dict[str, dict[str, set[str]]]:
    """Return allowed keys and optional diagnostics. Unreal requires every key."""
    errors = diagnostics if diagnostics is not None else []
    api: dict[str, dict[str, set[str]]] = {}
    sections = _sections(plan_text, "TOOL API")
    if len(sections) != 1:
        errors.append(f"expected one TOOL API section, found {len(sections)}")
        return api
    fences = _FENCE.findall(sections[0])
    if sections[0].count("```") != 2 * len(fences):
        errors.append("TOOL API contains an unclosed fence")
    for lang, body in fences:
        if lang.strip().lower() != "json":
            errors.append("TOOL API fence must be json")
            continue
        try:
            data = _json(body)
        except (ValueError, TypeError) as exc:
            errors.append(f"TOOL API invalid JSON: {exc}")
            continue
        tools = data.get("tools") if isinstance(data, dict) else data
        if not isinstance(tools, list) or not tools:
            errors.append("TOOL API tools must be a nonempty list")
            continue
        for tool in tools:
            if not isinstance(tool, dict):
                errors.append("TOOL API tool must be an object")
                continue
            full = tool.get("name")
            schema = tool.get("inputSchema", tool.get("input_schema"))
            if not isinstance(full, str) or not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+", full):
                errors.append("TOOL API tool name must be qualified")
                continue
            props = schema.get("properties") if isinstance(schema, dict) else None
            if not isinstance(props, dict) or any(not isinstance(v, dict) for v in props.values()):
                errors.append(f"TOOL API {full}: properties must be an object of schemas")
                continue
            toolset, _, name = full.rpartition(".")
            if name in api.get(toolset, {}):
                errors.append(f"TOOL API duplicate tool: {full}")
                continue
            api.setdefault(toolset, {})[name] = set(props)
    if not api:
        errors.append("TOOL API contains no valid tools")
    return api


def parse_call_ledger(artifact_text: str, diagnostics: list[str] | None = None) -> list[dict]:
    """Exactly one CALL LEDGER jsonl fence; retain diagnostics for invalid rows."""
    errors = diagnostics if diagnostics is not None else []
    entries: list[dict] = []
    markers = list(re.finditer(r"^(?:#{1,6}\s+)?CALL LEDGER[ \t]*$", artifact_text or "", re.MULTILINE))
    if len(markers) != 1:
        errors.append(f"expected one CALL LEDGER, found {len(markers)}")
        return entries
    match = re.match(r"\s*```jsonl[ \t]*\n(.*?)^```[ \t]*$", artifact_text[markers[0].end():], re.MULTILINE | re.DOTALL)
    if not match:
        errors.append("CALL LEDGER must have a closed jsonl fence")
        return entries
    for number, line in enumerate(match.group(1).splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = _json(line)
        except (ValueError, TypeError) as exc:
            errors.append(f"CALL LEDGER line {number}: invalid JSON ({exc})")
            continue
        if (not isinstance(entry, dict)
                or not isinstance(entry.get("toolset"), str) or not entry["toolset"].strip()
                or not isinstance(entry.get("tool"), str) or not entry["tool"].strip()
                or not isinstance(entry.get("args"), list)
                or any(not isinstance(arg, str) or not arg for arg in entry["args"])):
            errors.append(f"CALL LEDGER line {number}: expected toolset, tool, and string-list args")
            continue
        if len(entry["args"]) != len(set(entry["args"])):
            errors.append(f"CALL LEDGER line {number}: duplicate argument keys")
            continue
        entries.append(entry)
    return entries


def tool_call_gate(api: dict, entries: list[dict], artifact_title: str) -> list[dict]:
    flags: list[dict] = []
    for entry in entries:
        ts, tool = entry["toolset"], entry["tool"]
        base = {"artifact": artifact_title, "toolset": ts, "tool": tool}
        if ts not in api:
            flags.append({**base, "problem": "unknown toolset"})
            continue
        if tool not in api[ts]:
            flags.append({**base, "problem": "unknown tool"})
            continue
        supplied, expected = set(entry["args"]), api[ts][tool]
        for arg in sorted(supplied - expected):
            flags.append({**base, "problem": f"unknown argument: {arg}"})
        for arg in sorted(expected - supplied):
            flags.append({**base, "problem": f"missing argument: {arg}"})
    return flags


def _claim_evidence(plan: str, errors: list[str]) -> tuple[dict, list[dict]]:
    claims: dict[str, str] = {}
    verdicts: list[dict] = []
    for heading, marker in (("Plan", "CLAIMS: NONE"), ("Finding: engine", "VERDICTS: NONE")):
        sections = _sections(plan, heading)
        if len(sections) != 1:
            errors.append(f"expected one {heading} section, found {len(sections)}")
            continue
        body = _prose(sections[0])
        matches = list(_CLM_LINE.finditer(body))
        none_count = sum(line.strip() == marker for line in body.splitlines())
        if none_count > 1 or (none_count and matches):
            errors.append(f"{heading}: ambiguous {marker} declaration")
        if not matches and none_count != 1:
            errors.append(f"{heading}: no claim rows; use {marker} explicitly for zero claims")
        seen: set[str] = set()
        for match in matches:
            cid = _clm_id(match.group(1))
            body_text = match.group(2).strip()
            if cid in seen:
                errors.append(f"{heading}: duplicate {cid}")
            seen.add(cid)
            if heading == "Plan":
                if not body_text:
                    errors.append(f"Plan: empty claim {cid}")
                claims[cid] = body_text
            else:
                values = _VERDICT.findall(body_text)
                if len(values) != 1 or not re.match(r"^(VERIFIED|REJECTED|UNVERIFIABLE)\b", body_text, re.I):
                    errors.append(f"Finding: engine: {cid} needs exactly one leading verdict")
                else:
                    verdicts.append({"id": cid, "verdict": values[0].upper(), "line": match.group(0)})
        for line in body.splitlines():
            if re.search(r"\bCLM(?:[-_ ]?\d+|[-_]\w+)\b", line, re.I) and not _CLM_LINE.fullmatch(line):
                errors.append(f"{heading}: malformed claim row: {line.strip()}")
    verdict_ids = {v["id"] for v in verdicts}
    for cid in sorted(claims.keys() - verdict_ids):
        errors.append(f"missing verdict for {cid}")
    for cid in sorted(verdict_ids - claims.keys()):
        errors.append(f"unknown verdict ID {cid}")
    return claims, verdicts


def strip_gate_sections(plan_text: str) -> str:
    """Remove gate sections without interpreting code examples as headings."""
    from plan_sections import _headings
    try:
        headings = _headings(plan_text or "")
    except ValueError:
        # Preserve malformed source evidence for repair; never delete guessed spans.
        return plan_text or ""
    kept = plan_text or ""
    for index in reversed(range(len(headings))):
        start, _, title = headings[index]
        if re.fullmatch(r"Gate(?:\s+\([^\n]*\))?", title):
            end = headings[index + 1][0] if index + 1 < len(headings) else len(plan_text)
            kept = kept[:start] + kept[end:]
    return kept


def run(run_dir: Path) -> str:
    run_dir = Path(run_dir)
    manifest_file = run_dir / "run.json"
    if manifest_file.is_file():
        try:
            manifest = _json(manifest_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass  # The legacy gate below reports malformed evidence.
        else:
            if isinstance(manifest, dict) and manifest.get("workflow") == "packets-v1":
                return ("## Gate\n\nRESULT: INCONCLUSIVE. Packet runs use work_packets "
                        "status/finish; this legacy gate does not validate packets.\n")
    plan_path = run_dir / "plan.md"
    plan = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
    artifacts: list[tuple[str, str]] = []
    errors: list[str] = []
    artifact_task_ids: dict[str, str] = {}
    artifact_records: dict[str, dict] = {}
    manifest_path = run_dir / "run.json"
    if manifest_path.exists():
        try:
            from run_state import load_run
            manifest = _json(manifest_path.read_text(encoding="utf-8"))
            if (not isinstance(manifest, dict) or not isinstance(manifest.get("project_root"), str)
                    or not isinstance(manifest.get("uproject"), str)):
                raise ValueError("manifest requires project_root and uproject")
            state = load_run(Path(manifest["uproject"]), run_dir)
            artifact_records = state["artifacts"]
            paths = [run_dir / item["path"] for item in artifact_records.values()]
            artifact_task_ids = {Path(item["path"]).stem: item["task_id"]
                                 for item in state["artifacts"].values() if Path(item["path"]).suffix.lower() == ".md"}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"invalid run manifest: {exc}")
            paths = []
    else:
        paths = sorted((run_dir / "artifacts").glob("*.md"))
    for path in paths:
        if path.suffix.lower() != ".md":
            continue
        try:
            artifacts.append((path.stem, path.read_text(encoding="utf-8")))
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read artifact {path.name}: {exc}")

    api = parse_tool_api(plan, errors)
    for heading in ("PROJECT GPS", "Synthesis"):
        if len(_sections(plan, heading)) > 1:
            errors.append(f"duplicate {heading} sections")
    synthesis = _section(plan, "Synthesis")
    synthesis_prose = _prose(synthesis)
    build_headings = re.findall(r"^#*\s*BUILD\s+TASKS\b", synthesis_prose, re.MULTILINE | re.I)
    if len(build_headings) > 1:
        errors.append("duplicate BUILD TASKS blocks")
    build_tasks = parse_build_tasks(synthesis_prose, cap=1000)
    expected_tasks = {f"{index:02d}": task for index, task in enumerate(build_tasks, 1)}
    if build_headings and not expected_tasks:
        errors.append("BUILD TASKS has no parseable tasks")
    if manifest_path.exists():
        if len(_sections(plan, "Synthesis")) != 1:
            errors.append("manifest execution requires exactly one Synthesis section")
        if not build_headings or not expected_tasks:
            errors.append("manifest execution requires nonempty BUILD TASKS")
        from run_state import synthesis_hash
        try:
            current_synthesis = synthesis_hash(plan)
        except ValueError as exc:
            errors.append(f"invalid synthesis: {exc}")
        else:
            for name, record in artifact_records.items():
                if not current_synthesis or record.get("synthesis_sha256") != current_synthesis:
                    errors.append(f"{name}: artifact synthesis is stale or missing; reconcile and re-register")
    covered_tasks: set[str] = set()
    claims, verdicts = _claim_evidence(plan, errors)
    unsupported = [claims[v["id"]] for v in verdicts
                   if v["verdict"] in {"REJECTED", "UNVERIFIABLE"} and v["id"] in claims]
    # Only validated API names ground symbols: prose descriptions/rejections do not.
    grounded = _section(plan, "PROJECT GPS") + "\n" + "\n".join(
        f"{ts}.{tool}" for ts, tools in api.items() for tool in tools)
    g_flags = grounding_gate(unsupported, artifacts, grounded)
    t_flags: list[dict] = []
    call_count = 0
    for title, text in artifacts:
        prose = _prose(text)
        lanes = re.findall(r"^Lane:[ \t]*(\S+)[ \t]*$", prose, re.MULTILINE | re.I)
        if len(lanes) != 1 or lanes[0].lower() not in LANES:
            errors.append(f"{title}: requires exactly one valid Lane: declaration")
        if expected_tasks:
            ordinal = re.match(r"^(\d{2})(?:-|$)", title)
            task_id = (artifact_task_ids.get(title) if manifest_path.exists()
                       else ordinal.group(1) if ordinal else None)
            if task_id not in expected_tasks:
                errors.append(f"{title}: unknown or missing build task ID {task_id!r}")
            else:
                if task_id in covered_tasks:
                    errors.append(f"duplicate artifact coverage for build task {task_id}")
                covered_tasks.add(task_id)
                if len(lanes) == 1 and lanes[0].lower() != expected_tasks[task_id]["lane"]:
                    errors.append(f"{title}: lane does not match build task {task_id}")
        exemptions = len(re.findall(r"^NO TOOL CALLS[ \t]*$", prose, re.MULTILINE))
        exempt = len(lanes) == 1 and lanes[0].lower() == "needs-you" and exemptions == 1
        has_ledger = bool(re.search(r"^(?:#{1,6}\s+)?CALL LEDGER[ \t]*$", text, re.MULTILINE))
        ledger_errors: list[str] = []
        entries = parse_call_ledger(text, ledger_errors) if has_ledger or not exempt else []
        errors.extend(f"{title}: {error}" for error in ledger_errors)
        if exemptions and (not exempt or entries):
            errors.append(f"{title}: NO TOOL CALLS requires needs-you with no calls")
        if not entries and not exempt:
            errors.append(f"{title}: a nonempty valid CALL LEDGER is required")
        call_count += len(entries)
        t_flags.extend(tool_call_gate(api, entries, title))

    for task_id in sorted(expected_tasks.keys() - covered_tasks):
        errors.append(f"missing artifact for build task {task_id}: {expected_tasks[task_id]['title']}")

    status = "FAIL" if errors or g_flags or t_flags else "PASS"
    if (not artifacts and not errors) or not plan.strip():
        status = "INCONCLUSIVE"
    elif not artifacts and not manifest_path.exists():
        status = "INCONCLUSIVE"
    lines = ["## Gate", ""]
    if not artifacts:
        lines.append("INCONCLUSIVE: no artifacts found under artifacts/.")
    lines.append(f"Evidence gate: {'FAIL' if errors else 'PASS'}.")
    lines.extend(f"- {error}" for error in errors)
    lines.append(f"Grounding gate: {'FAIL' if g_flags else 'PASS'} "
                 f"({len(unsupported)} unsupported claim(s), {len(artifacts)} artifact(s) scanned).")
    for flag in g_flags:
        lines.append(f"- forbidden symbol {flag['symbol']!r} in artifact '{flag['artifact']}'")
    lines.append(f"Tool-call gate: {'FAIL' if t_flags else 'PASS'} ({call_count} call(s) checked).")
    for flag in t_flags:
        lines.append(f"- {flag['toolset']}.{flag['tool']} in '{flag['artifact']}': {flag['problem']}")
    lines.append("")
    lines.append(f"RESULT: {status}. " + ("The Validator still performs the prose-level scan." if status == "PASS"
                 else "The Validator may not sign off; supply complete, valid evidence and re-run."))
    section = "\n".join(lines) + "\n"
    kept = strip_gate_sections(plan).rstrip("\n")
    from plan_sections import write_plan
    write_plan(plan_path, (kept + "\n" if kept else "") + "\n" + section)
    return section


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python gates.py <run_dir>", file=sys.stderr)
        sys.exit(2)
    out = run(Path(sys.argv[1]))
    print(out)
    sys.exit(2 if "RESULT: INCONCLUSIVE" in out else 1 if "RESULT: FAIL" in out else 0)
