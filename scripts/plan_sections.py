"""Replace a Wright report section without accumulating stale revisions."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import tempfile


def _headings(text: str) -> list[tuple[int, int, str]]:
    headings = []
    offset = 0
    fence = None
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        marker = re.match(r"(`{3,}|~{3,})", stripped)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not stripped[len(token):].strip():
                fence = None
        elif fence is None:
            match = re.match(r"^## ([^\r\n]+)", line)
            if match:
                headings.append((offset, offset + len(line), match.group(1).strip()))
        offset += len(line)
    if fence is not None:
        raise ValueError("unclosed Markdown fence")
    return headings


def split_sections(text: str) -> list[tuple[str, str]]:
    headings = _headings(text)
    return [(heading, text[end:headings[i + 1][0] if i + 1 < len(headings) else len(text)])
            for i, (_, end, heading) in enumerate(headings)]


def replace_section(text: str, heading: str, body: str) -> str:
    if not heading.strip() or any(c in heading for c in "\r\n"):
        raise ValueError("section heading must be a nonempty single line")
    headings = _headings(text)
    matches = [i for i, item in enumerate(headings) if item[2] == heading]
    if len(matches) > 1:
        raise ValueError(f"duplicate section: {heading}")
    # Worker headings remain subordinate; code and DSL are preserved byte-for-byte.
    for start, _, _ in reversed(_headings(body)):
        body = body[:start] + "#" + body[start:]
    section = f"## {heading}\n\n{body.strip()}\n\n"
    if matches:
        i = matches[0]
        start = headings[i][0]
        end = headings[i + 1][0] if i + 1 < len(headings) else len(text)
        return text[:start] + section + text[end:]
    return text.rstrip() + "\n\n" + section


def update_plan(path: Path, heading: str, body: str) -> None:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    updated = replace_section(text, heading, body)
    write_plan(path, updated)


def write_plan(path: Path, text: str) -> None:
    """Atomically publish a full report after the caller validates its contents."""
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, prefix=".plan-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("heading")
    parser.add_argument("body_file", type=Path)
    args = parser.parse_args()
    try:
        update_plan(args.plan, args.heading, args.body_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    main()
