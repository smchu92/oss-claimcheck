import json
from pathlib import Path

from link_evidence_pack.core import prepare_evidence_pack, parse_repo_ref, render_markdown


def test_parse_repo_ref_accepts_owner_repo():
    repo = parse_repo_ref("openai/codex")

    assert repo.owner == "openai"
    assert repo.name == "codex"
    assert repo.url == "https://github.com/openai/codex"


def test_prepare_evidence_pack_returns_structured_claim_sections():
    pack = prepare_evidence_pack(
        url="https://x.com/example/status/123",
        claim_text="This tool replaces manual OSS adoption review and works everywhere.",
        repo="openai/codex",
    )

    assert pack["source"]["url"] == "https://x.com/example/status/123"
    assert pack["claim"]["text"] == "This tool replaces manual OSS adoption review and works everywhere."
    assert pack["repository"]["full_name"] == "openai/codex"
    assert pack["repository"]["url"] == "https://github.com/openai/codex"
    assert "official repository exists" in pack["verification_checklist"]
    assert pack["status"]["confirmed"] == []
    assert "works everywhere" in pack["status"]["hype_signals"]
    assert pack["follow_up_questions"]


def test_render_markdown_contains_maintainer_review_sections():
    pack = prepare_evidence_pack(
        url="https://x.com/example/status/123",
        claim_text="This agent does PhD work in seconds.",
        repo="owner/repo",
    )

    markdown = render_markdown(pack)

    assert "# Evidence Pack" in markdown
    assert "## Source" in markdown
    assert "## Claim" in markdown
    assert "## Repository" in markdown
    assert "## Confirmed" in markdown
    assert "## Unverified" in markdown
    assert "## Hype signals" in markdown
    assert "does PhD work in seconds" in markdown


def test_prepare_evidence_pack_can_include_github_metadata_from_fetcher():
    def fake_fetcher(repo):
        assert repo.full_name == "openai/codex"
        return {
            "description": "Lightweight coding agent",
            "stars": 1234,
            "forks": 56,
            "default_branch": "main",
            "license": "Apache-2.0",
            "updated_at": "2026-06-01T00:00:00Z",
        }

    pack = prepare_evidence_pack(
        url="https://x.com/example/status/123",
        claim_text="This tool replaces all reviewers.",
        repo="openai/codex",
        github_fetcher=fake_fetcher,
    )

    assert pack["repository"]["verification_status"] == "github metadata fetched"
    assert pack["repository"]["stars"] == 1234
    assert "GitHub metadata fetched for openai/codex" in pack["status"]["confirmed"]


def test_cli_prepare_writes_json_and_markdown(tmp_path):
    from link_evidence_pack.cli import main

    output_dir = tmp_path / "evidence"
    exit_code = main([
        "prepare",
        "--url", "https://x.com/example/status/123",
        "--claim-text", "This tool replaces all reviewers.",
        "--repo", "owner/repo",
        "--output-dir", str(output_dir),
    ])

    assert exit_code == 0
    evidence_json = output_dir / "evidence.json"
    evidence_md = output_dir / "evidence.md"
    assert evidence_json.exists()
    assert evidence_md.exists()

    data = json.loads(evidence_json.read_text())
    assert data["repository"]["full_name"] == "owner/repo"
    assert "## Hype signals" in evidence_md.read_text()
