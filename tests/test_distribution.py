import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_skill_metadata_covers_both_agents_and_core_trigger_intents() -> None:
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "name: narrated-app-demo" in skill
    assert "license: MIT" in skill
    assert 'compatibility: "Codex and Claude Code;' in skill
    for trigger in ("product walkthrough", "screen tutorial", "demo video", "Playwright recording"):
        assert trigger in skill


def test_readme_has_dual_agent_installation_and_valid_cli_examples() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Agentic AI skill compatible with Codex and Claude Code" in readme
    assert "~/.codex/skills/narrated-app-demo" in readme
    assert "~/.claude/skills/narrated-app-demo" in readme
    assert "scripts.generate_audio --manifest production.json --chapter 01-introduction" in readme
    assert "scripts.validate_audio chapters/01-introduction.mp3" in readme
    assert "scripts.assemble_audio --manifest production.json" in readme
    assert "scripts.validate_audio path/to/manifest.json" not in readme


def test_skill_evals_are_realistic_and_objectively_checkable() -> None:
    payload = json.loads((ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))

    assert payload["skill_name"] == "narrated-app-demo"
    assert len(payload["evals"]) == 3
    assert len({item["id"] for item in payload["evals"]}) == 3
    for item in payload["evals"]:
        assert item["prompt"]
        assert item["expected_output"]
        assert item["files"] == []
        assert len(item["expectations"]) >= 4
