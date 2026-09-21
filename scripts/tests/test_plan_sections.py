import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import plan_sections


def test_revisions_replace_old_body_and_preserve_other_sections():
    plan = "# Run\n\n## Synthesis\nold\n\n## Close\nkeep\n"
    result = plan_sections.replace_section(plan, "Synthesis", "new")
    assert result.count("## Synthesis\n") == 1
    assert "old" not in result and "new" in result
    assert dict(plan_sections.split_sections(result))["Close"].strip() == "keep"


def test_worker_headings_demoted_but_fenced_data_unchanged():
    body = '## Verdicts\nCLM-1: VERIFIED\n```text\n## literal\n```\n'
    result = plan_sections.replace_section("# Run", "Finding: engine", body)
    assert "### Verdicts" in result
    assert "```text\n## literal\n```" in result
    assert [name for name, _ in plan_sections.split_sections(result)] == ["Finding: engine"]


@pytest.mark.parametrize("fence", ["```", "~~~~"])
def test_headings_inside_fences_do_not_replace_real_section(fence):
    plan = f"# Run\n{fence}text\n## Gate\nexample\n{fence}\n\n## Gate\nold\n"
    result = plan_sections.replace_section(plan, "Gate", "new")
    assert "example" in result and "old" not in result
    assert dict(plan_sections.split_sections(result))["Gate"].strip() == "new"


@pytest.mark.parametrize("plan", ["## Gate\na\n## Gate\nb\n", "## Gate\n```text\nbroken"])
def test_ambiguous_plan_is_rejected(plan):
    with pytest.raises(ValueError):
        plan_sections.replace_section(plan, "Gate", "new")


def test_failed_replace_keeps_original(tmp_path, monkeypatch):
    path = tmp_path / "plan.md"
    path.write_text("# Run\n", encoding="utf-8")
    def fail(*args):
        raise OSError("simulated interrupted replace")
    monkeypatch.setattr(plan_sections.os, "replace", fail)
    with pytest.raises(OSError):
        plan_sections.update_plan(path, "Gate", "new")
    assert path.read_text(encoding="utf-8") == "# Run\n"
    assert list(tmp_path.iterdir()) == [path]
