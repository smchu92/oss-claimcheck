import json
from pathlib import Path

from oss_claimcheck.core import prepare_evidence_pack, parse_repo_ref, render_markdown


def test_parse_repo_ref_accepts_owner_repo():
    repo = parse_repo_ref("openai/codex")

    assert repo.owner == "openai"
    assert repo.name == "codex"
    assert repo.url == "https://github.com/openai/codex"


def test_parse_repo_ref_accepts_canonical_github_url():
    repo = parse_repo_ref("https://github.com/openai/codex")

    assert repo.owner == "openai"
    assert repo.name == "codex"


def test_parse_repo_ref_rejects_malformed_or_suspicious_values():
    bad_values = [
        "openai",
        "openai/codex/extra",
        "../codex",
        "openai/co dex",
        "https://evil.example/openai/codex",
        "https://github.com/openai/../codex",
    ]

    for value in bad_values:
        try:
            parse_repo_ref(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {value!r}")


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


def test_prepare_evidence_pack_extracts_official_source_quotes():
    pack = prepare_evidence_pack(
        url="https://x.com/example/status/123",
        claim_text="This tool generates evidence packs for OSS adoption review.",
        official_sources=[{
            "title": "README",
            "url": "https://github.com/example/tool",
            "text": "A generic intro. This tool generates evidence packs for OSS maintainers before adoption. Another sentence.",
        }],
    )

    sources = pack["official_sources"]
    assert sources[0]["title"] == "README"
    assert sources[0]["quotes"] == ["This tool generates evidence packs for OSS maintainers before adoption."]
    markdown = render_markdown(pack)
    assert "## Official source quotes" in markdown
    assert "This tool generates evidence packs" in markdown


def test_prepare_evidence_pack_includes_repository_signals_from_github_metadata():
    def fake_fetcher(repo):
        return {
            "description": "Lightweight coding agent",
            "license": "Apache-2.0",
            "readme_present": True,
            "package_files": ["pyproject.toml"],
            "release_count": 2,
        }

    pack = prepare_evidence_pack(
        url="https://x.com/example/status/123",
        claim_text="This tool replaces manual OSS adoption review.",
        repo="openai/codex",
        github_fetcher=fake_fetcher,
    )

    signals = pack["repository"]["signals"]
    assert signals["readme_present"] is True
    assert signals["license_present"] is True
    assert signals["package_files"] == ["pyproject.toml"]
    assert signals["release_count"] == 2
    assert "README detected" in pack["status"]["confirmed"]
    assert "License detected: Apache-2.0" in pack["status"]["confirmed"]
    assert "Package metadata detected: pyproject.toml" in pack["status"]["confirmed"]


def test_cli_prepare_rejects_unsafe_source_url(tmp_path):
    from oss_claimcheck.cli import main

    try:
        main([
            "prepare",
            "--url", "file:///etc/passwd",
            "--claim-text", "This tool supports adoption review evidence packs.",
            "--output-dir", str(tmp_path / "evidence"),
        ])
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("expected CLI to reject unsafe source URL")


def test_cli_prepare_rejects_dangerous_output_dir(tmp_path, monkeypatch):
    from oss_claimcheck.cli import main

    monkeypatch.chdir(tmp_path)
    try:
        main([
            "prepare",
            "--url", "https://x.com/example/status/123",
            "--claim-text", "This tool supports adoption review evidence packs.",
            "--output-dir", str(tmp_path),
        ])
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("expected CLI to reject dangerous output dir")


def test_cli_prepare_accepts_official_source_text_file(tmp_path):
    from oss_claimcheck.cli import main

    source_file = tmp_path / "source.txt"
    source_file.write_text("The official README says this tool supports adoption review evidence packs.")
    output_dir = tmp_path / "evidence"

    exit_code = main([
        "prepare",
        "--url", "https://x.com/example/status/123",
        "--claim-text", "This tool supports adoption review evidence packs.",
        "--official-source-title", "README",
        "--official-source-url", "https://github.com/example/tool",
        "--official-source-text-file", str(source_file),
        "--output-dir", str(output_dir),
    ])

    assert exit_code == 0
    data = json.loads((output_dir / "evidence.json").read_text())
    assert data["official_sources"][0]["quotes"]
    assert "## Official source quotes" in (output_dir / "evidence.md").read_text()


def test_prepare_evidence_pack_includes_codex_prompt_suggestions_for_hype_signals():
    pack = prepare_evidence_pack(
        url="https://x.com/example/status/123",
        claim_text="This tool replaces all reviewers with zero setup.",
        repo="owner/repo",
    )

    prompts = pack["codex_smoke_test_prompts"]
    assert len(prompts) >= 4
    assert prompts[0]["category"] == "installation"
    assert prompts[0]["suggested"] is True
    assert "owner/repo" in prompts[0]["prompt"]
    assert "zero setup" in prompts[0]["references"]
    assert any(prompt["category"] == "failure-mode review" for prompt in prompts)

    markdown = render_markdown(pack)
    assert "## Codex-ready follow-up prompts" in markdown
    assert "Suggested — verify before relying on this task" in markdown
    assert "zero setup" in markdown


def test_cli_prepare_writes_json_and_markdown(tmp_path):
    from oss_claimcheck.cli import main

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
    assert "codex_smoke_test_prompts" in data
    assert "## Hype signals" in evidence_md.read_text()
    assert "## Codex-ready follow-up prompts" in evidence_md.read_text()
