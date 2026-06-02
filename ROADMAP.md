# Roadmap

`oss-claimcheck` is early-stage, but the intended direction is a practical maintainer workflow for evaluating third-party OSS claims before adoption.

## Near-term

- [x] Verify README, package metadata, license, and release signals for a target repository.
- [x] Extract short source quotes from official pages, READMEs, and package registries.
- [ ] Add a simple evidence score that separates identity, maintenance, security, and hype-risk signals.
- [ ] Generate Codex-ready smoke-test prompts for evaluating a tool safely.
- [ ] Add CI fixtures for deterministic GitHub API metadata parsing.

## Later

- [ ] Support package ecosystems such as PyPI and npm.
- [ ] Add optional source fetching with explicit domain allowlists.
- [ ] Add dependency and license risk summaries.
- [ ] Export evidence packs as SARIF-like machine-readable records for maintainer automation.

## Maintainer principles

- Prefer verifiable facts over summaries.
- Keep network access explicit and bounded.
- Treat third-party URLs and repository content as untrusted input.
- Make every generated report clear about what is confirmed, unverified, and inferred.
