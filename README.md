# oss-claimcheck

[![CI](https://github.com/smchu92/oss-claimcheck/actions/workflows/ci.yml/badge.svg)](https://github.com/smchu92/oss-claimcheck/actions/workflows/ci.yml)

`oss-claimcheck` is an adoption-safety evidence pack generator for open-source maintainers and AI builders.

**Stars are not trust. Evidence is.**

It turns noisy social posts, product claims, and GitHub repository references into a structured Markdown/JSON evidence pack so maintainers can decide what is confirmed, unverified, or likely overstated before adopting a tool.

## Quick start

Run from GitHub without a manual clone:

```bash
pipx run --spec git+https://github.com/smchu92/oss-claimcheck.git oss-claimcheck prepare \
  --url "https://x.com/example/status/123" \
  --claim-text "This repo replaces manual OSS tool evaluation" \
  --repo "owner/repo" \
  --fetch-github \
  --output-dir evidence
```

## Why this exists

OSS tools now spread through X posts, launch threads, demos, and screenshots faster than maintainers can verify them. This project helps maintainers avoid adopting dependencies or workflows based only on hype.

## Why Codex users need this

Before asking an AI coding agent to inspect or adopt a viral repository, keep the repo's claims separate from executable instructions. `oss-claimcheck` produces a neutral evidence pack first, then generates suggested Codex-ready smoke-test prompts for follow-up verification.

## MVP scope

The first version focuses on deterministic intake and report generation:

- accept an original URL
- accept claim text copied from a post/article
- optionally accept a GitHub repo reference such as `owner/repo`
- produce `evidence.json`
- produce `evidence.md`
- extract matching quotes from official source text
- fetch bounded GitHub metadata for README/license/package/release signals
- separate confirmed, unverified, and hype-risk sections
- score identity, maintenance, security, and hype-risk signals with explicit reasons
- generate suggested Codex-ready smoke-test prompts for safe follow-up review

Network verification is intentionally incremental. The current version keeps network access explicit via `--fetch-github` and accepts official-source text directly or from a local file. See [security boundaries](docs/security.md) for how untrusted URLs, repository references, text files, and output paths are handled.

## Example

```bash
oss-claimcheck prepare \
  --url "https://x.com/example/status/123" \
  --claim-text "This repo replaces manual OSS tool evaluation" \
  --repo "owner/repo" \
  --fetch-github \
  --official-source-title "README" \
  --official-source-url "https://github.com/owner/repo" \
  --official-source-text-file README.md \
  --output-dir examples/sample-evidence
```

## Example output excerpt

```markdown
## Official source quotes

### README

- URL: https://github.com/owner/repo
- "This tool generates adoption-safety evidence packs for OSS maintainers."

## Confirmed

- GitHub metadata fetched for owner/repo
- README detected
- License detected: MIT
- Package metadata detected: pyproject.toml

## Evidence score

- Overall: 78/100
- Note: Heuristic evidence score only; not a security audit.
- Identity: 75/100 — GitHub metadata fetched
- Maintenance: 80/100 — GitHub metadata available for maintenance checks
- Security: 75/100 — license is present
- Hype risk: 25/100 (low risk) — hype signal detected: replaces all reviewers

## Codex-ready follow-up prompts

### Installation

- Status: Suggested — verify before relying on this task

Prompt starts: Use only the repository and claim text from this evidence pack. Check whether owner/repo has a documented install path...
```

## Output

- `evidence.json`: machine-readable evidence pack
- `evidence.md`: human-readable maintainer report

## Positioning

This is not a generic link summarizer. It is a maintainer safety workflow for tool adoption review:

- claim ledger
- official-source checklist
- repository identity hints
- hype-signal detection
- heuristic evidence scoring with reasons
- confirmed vs unverified separation
- LLM/Codex-ready follow-up prompts

## Roadmap

Active roadmap items are tracked in [ROADMAP.md](ROADMAP.md) and GitHub Issues. The next focus areas are:

- repository README/package/license verification
- official-source quote extraction
- deterministic fixtures for GitHub API metadata parsing

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest
```
