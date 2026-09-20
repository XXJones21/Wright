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
    r"^[\s>*_`-]*`?(CLM[\s_-]?\d+)`?[\s:.)\]\-]*(.*?)\s*$",
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
    return f"CLM-{m.group(0)}" if m else None


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
    gps_n = _norm(gps_text)
    forbidden: dict[str, str] = {}
    for claim in rejected_claim_texts:
        for s in extract_symbols(claim):
            ns = _norm(s)
            if len(ns) < 6:
                continue
            if ns not in gps_n:
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


_FENCE = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)


def parse_tool_api(plan_text: str) -> dict[str, dict[str, set[str]]]:
    """Read every fenced json block under `## TOOL API` (up to the next `## `
    heading) and index toolset -> tool -> allowed argument keys."""
    api: dict[str, dict[str, set[str]]] = {}
    m = re.search(r"^## TOOL API\s*$(.*?)(?=^## |\Z)", plan_text or "", re.MULTILINE | re.DOTALL)
    if not m:
        return api
    for lang, body in _FENCE.findall(m.group(1)):
        if (lang or "").lower() != "json":
            continue
        try:
            d = json.loads(body)
        except json.JSONDecodeError:
            continue
        tools = d.get("tools") if isinstance(d, dict) else d
        for t in tools or []:
            full = t.get("name", "")
            toolset, _, tool = full.rpartition(".")
            props = ((t.get("inputSchema") or t.get("input_schema") or {}).get("properties") or {})
            api.setdefault(toolset, {})[tool] = set(props.keys())
    return api


def parse_call_ledger(artifact_text: str) -> list[dict]:
    """The `CALL LEDGER` jsonl fence in an artifact: one call per line."""
    entries: list[dict] = []
    m = re.search(r"CALL LEDGER\s*```jsonl\n(.*?)```", artifact_text or "", re.DOTALL)
    if not m:
        return entries
    for ln in m.group(1).splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(e, dict) and "toolset" in e and "tool" in e:
            e.setdefault("args", [])
            entries.append(e)
    return entries


def tool_call_gate(api: dict, entries: list[dict], artifact_title: str) -> list[dict]:
    flags: list[dict] = []
    for e in entries:
        ts, tool = e["toolset"], e["tool"]
        base = {"artifact": artifact_title, "toolset": ts, "tool": tool}
        if ts not in api:
            flags.append({**base, "problem": "unknown toolset"})
            continue
        if tool not in api[ts]:
            flags.append({**base, "problem": "unknown tool"})
            continue
        for a in e.get("args", []):
            if a not in api[ts][tool]:
                flags.append({**base, "problem": f"unknown argument: {a}"})
    return flags


def _section(plan_text: str, heading_prefix: str) -> str:
    m = re.search(rf"^## {re.escape(heading_prefix)}.*?$(.*?)(?=^## |\Z)", plan_text, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else ""


def run(run_dir: Path) -> str:
    run_dir = Path(run_dir)
    plan_path = run_dir / "plan.md"
    plan = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
    artifacts: list[tuple[str, str]] = []
    for p in sorted((run_dir / "artifacts").glob("*.md")) if (run_dir / "artifacts").exists() else []:
        artifacts.append((p.stem, p.read_text(encoding="utf-8")))

    gps = _section(plan, "PROJECT GPS")
    claims = parse_clm_claims(_section(plan, "Plan"))
    verdicts = parse_clm_verdicts(_section(plan, "Finding: engine"))
    rejected = [claims[v["id"]] for v in verdicts if v["verdict"] == "REJECTED" and v["id"] in claims]
    g_flags = grounding_gate(rejected, artifacts, gps)

    api = parse_tool_api(plan)
    t_flags: list[dict] = []
    for title, text in artifacts:
        t_flags += tool_call_gate(api, parse_call_ledger(text), title)

    lines = ["## Gate", ""]
    if not artifacts:
        lines.append("INCONCLUSIVE: no artifacts found under artifacts/.")
        status = "INCONCLUSIVE"
    else:
        status = "PASS" if not g_flags and not t_flags else "FAIL"
        lines.append(f"Grounding gate: {'PASS' if not g_flags else 'FAIL'} "
                     f"({len(rejected)} rejected claim(s), {len(artifacts)} artifact(s) scanned).")
        for f in g_flags:
            lines.append(f"- forbidden symbol {f['symbol']!r} in artifact '{f['artifact']}'")
        if not api:
            lines.append("Tool-call gate: INCONCLUSIVE (no TOOL API section in the plan).")
            if status == "PASS":
                status = "INCONCLUSIVE"
        else:
            lines.append(f"Tool-call gate: {'PASS' if not t_flags else 'FAIL'} "
                         f"({sum(len(parse_call_ledger(t)) for _, t in artifacts)} call(s) checked).")
            for f in t_flags:
                lines.append(f"- {f['toolset']}.{f['tool']} in '{f['artifact']}': {f['problem']}")
        lines.append("")
        lines.append(f"RESULT: {status}. " + ("The Validator may not sign off; the builder must re-emit." if status == "FAIL"
                     else "The Validator still performs the prose-level scan."))
    section = "\n".join(lines) + "\n"
    with plan_path.open("a", encoding="utf-8") as fh:
        fh.write("\n" + section)
    return section


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python gates.py <run_dir>", file=sys.stderr)
        sys.exit(2)
    out = run(Path(sys.argv[1]))
    print(out)
    sys.exit(1 if "RESULT: FAIL" in out else 0)
