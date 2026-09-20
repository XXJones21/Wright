"""Deterministic gates for a Wright run. Pure Python, no model, no network.

Ported from Valar's wright_plan.py (grounding gate, claim/verdict parsers) and
extended with lane tags on build tasks and a tool-call gate (see part 2).
"""
from __future__ import annotations

import re

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
