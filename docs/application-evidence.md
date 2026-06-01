# Codex for Open Source application evidence

## Project

`link-evidence-pack` — an adoption-safety evidence pack generator for OSS maintainers.

## Application framing

This project helps OSS maintainers and AI builders evaluate tools before adoption by turning noisy social posts, GitHub repository references, and product claims into structured evidence packs. It separates claims, sources, repository identity, hype signals, and verification status, reducing the risk of adopting dependencies or workflows based on unverified marketing claims.

## Codex/API credit use

API credits would be used for maintainer workflows such as:

- claim extraction from noisy posts and launch threads
- source-grounded verification summaries
- PR review automation for new verification rules
- documentation generation
- benchmark/evidence summarization for OSS tool adoption reviews

## Evidence checklist before applying

- [ ] Public GitHub repo exists
- [ ] CLI runs locally
- [ ] Tests pass
- [ ] Sample `evidence.md` and `evidence.json` exist
- [ ] README explains maintainer safety value
- [ ] CI workflow exists
- [ ] v0.1.0 tag or release exists
