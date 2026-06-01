# link-evidence-pack

`link-evidence-pack` is an adoption-safety evidence pack generator for open-source maintainers and AI builders.

It turns noisy social posts, product claims, and GitHub repository references into a structured Markdown/JSON evidence pack so maintainers can decide what is confirmed, unverified, or likely overstated before adopting a tool.

## Why this exists

OSS tools now spread through X posts, launch threads, demos, and screenshots faster than maintainers can verify them. This project helps maintainers avoid adopting dependencies or workflows based only on hype.

## MVP scope

The first version focuses on deterministic intake and report generation:

- accept an original URL
- accept claim text copied from a post/article
- optionally accept a GitHub repo reference such as `owner/repo`
- produce `evidence.json`
- produce `evidence.md`
- separate confirmed, unverified, and hype-risk sections

Network verification is intentionally incremental. The first working version supports offline/static report generation, then GitHub API verification will be added as a bounded follow-up.

## Example

```bash
link-evidence-pack prepare \
  --url "https://x.com/example/status/123" \
  --claim-text "This repo replaces manual OSS tool evaluation" \
  --repo "owner/repo" \
  --fetch-github \
  --output-dir examples/sample-evidence
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
- confirmed vs unverified separation
- LLM/Codex-ready follow-up questions

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```
