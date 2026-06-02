# Untrusted Input Safety Boundaries Implementation Plan

> **For Hermes:** Implement with strict TDD. Do not add broad crawler/network features. Keep scope to issue #5 safety boundaries.

**Goal:** Make `oss-claimcheck` safer around untrusted repo strings, source URLs, source text files, and output paths.

**Architecture:** Add small validation helpers in `src/oss_claimcheck/safety.py`, wire them into `core.py` and `cli.py`, document boundaries in `docs/security.md`, then update README/ROADMAP and close issue #5 after CI passes.

**Tech Stack:** Python stdlib only, pytest, argparse CLI.

---

## Scope

### In scope
- Strict GitHub repo reference validation.
- Source URL scheme validation for user-provided source URLs.
- Output directory guardrails to avoid writing to dangerous filesystem roots.
- Official source text file guardrails: must be local file, must exist, must not be too large.
- Document untrusted-input policy and future network-fetching constraints.

### Out of scope
- Full URL crawling.
- HTML parsing.
- Sandbox execution.
- Malware/security scanning.
- Automatic verdicts like “safe/unsafe”.

---

## Acceptance Criteria

- Malformed repo refs fail before evidence pack generation.
- Repo refs with traversal/control/extra path segments are rejected.
- Source URLs allow only `http://` and `https://`.
- CLI refuses dangerous output directories such as `/`, `$HOME`, and the repo root.
- CLI refuses official source text files over a small default limit.
- `docs/security.md` documents current safety boundaries and future fetching rules.
- Tests pass: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q`.
- Build passes: `python3 -m build`.

---

## Task 1: Add repo parser safety tests

**Objective:** Lock down malformed repo behavior before changing parser code.

**Files:**
- Modify: `tests/test_evidence_pack.py`

**Test cases:**
- `parse_repo_ref("openai")` raises `ValueError`
- `parse_repo_ref("openai/codex/extra")` raises `ValueError`
- `parse_repo_ref("../codex")` raises `ValueError`
- `parse_repo_ref("openai/co dex")` raises `ValueError`
- `parse_repo_ref("https://evil.example/openai/codex")` raises `ValueError`
- `parse_repo_ref("https://github.com/openai/codex")` still passes

**Verify RED:**
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_evidence_pack.py -q
```
Expected: new malformed cases fail because parser is too permissive.

---

## Task 2: Implement strict repo validation

**Objective:** Make `parse_repo_ref` accept only GitHub `owner/repo` or canonical GitHub URL.

**Files:**
- Modify: `src/oss_claimcheck/core.py`

**Implementation notes:**
- Accept `owner/repo`.
- Accept `https://github.com/owner/repo`.
- Reject other URL hosts.
- Reject extra path segments.
- Use regex for each component: `^[A-Za-z0-9_.-]+$`.
- Reject `.` and `..` components.
- Keep error message simple: `repo must be an owner/name pair or GitHub URL`.

**Verify GREEN:**
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_evidence_pack.py -q
```
Expected: all parser tests pass.

---

## Task 3: Add safety helper tests

**Objective:** Define CLI-facing safety guard behavior in a dedicated module.

**Files:**
- Create/Modify: `tests/test_safety.py`
- Create: `src/oss_claimcheck/safety.py`

**Tests to write first:**
- `validate_source_url("https://x.com/a")` returns same URL.
- `validate_source_url("http://example.com")` returns same URL.
- `validate_source_url("file:///etc/passwd")` raises `ValueError`.
- `validate_source_url("javascript:alert(1)")` raises `ValueError`.
- `validate_output_dir(tmp_path / "out")` passes.
- `validate_output_dir(Path("/"))` raises `ValueError`.
- `validate_output_dir(Path.home())` raises `ValueError`.
- `read_limited_text_file(file, max_bytes=10)` rejects files over limit.

**Verify RED:**
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_safety.py -q
```
Expected: import/function failures before implementation.

---

## Task 4: Implement safety helpers

**Objective:** Add small stdlib-only validators.

**Files:**
- Create: `src/oss_claimcheck/safety.py`

**Functions:**
- `validate_source_url(url: str) -> str`
  - use `urllib.parse.urlparse`
  - allow schemes: `http`, `https`
  - require hostname
- `validate_output_dir(path: Path) -> Path`
  - resolve path without requiring existence where possible
  - reject filesystem root
  - reject home directory itself
  - reject current working directory itself to avoid spraying files into repo root by accident
- `read_limited_text_file(path: Path, *, max_bytes: int = 200_000) -> str`
  - reject non-files
  - reject files bigger than limit
  - read UTF-8 text

**Verify GREEN:**
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_safety.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
```
Expected: all tests pass.

---

## Task 5: Wire validators into CLI

**Objective:** Enforce safety boundaries during normal CLI use.

**Files:**
- Modify: `src/oss_claimcheck/cli.py`
- Modify: `tests/test_evidence_pack.py` or `tests/test_cli_safety.py`

**Behavior:**
- Validate `--url` before pack generation.
- Validate `--output-dir` before writing.
- Use `read_limited_text_file` for `--official-source-text-file`.
- If validation fails, let argparse-style exit happen or return nonzero with clear error. Prefer a small parser error helper for consistent CLI behavior.

**Tests:**
- CLI rejects `--url file:///tmp/source`.
- CLI rejects dangerous output dir.
- CLI rejects too-large source text file using a small injected/helper limit if practical.

**Verify:**
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
```
Expected: all tests pass.

---

## Task 6: Document security boundaries

**Objective:** Make safety posture visible for maintainers and reviewers.

**Files:**
- Create: `docs/security.md`
- Modify: `README.md`
- Modify: `ROADMAP.md`

**Document:**
- All user-provided URLs/content are untrusted.
- Current tool does not crawl arbitrary pages by default.
- `--fetch-github` only calls GitHub API for validated `owner/repo`.
- Official source text is local/user-provided and size-limited.
- Output writing is guarded against dangerous roots.
- Future fetching must use explicit domain allowlists and size/time limits.

**Verify:**
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
python3 -m build
```
Expected: tests and build pass.

---

## Task 7: Commit, push, CI, close issue #5

**Objective:** Publish the safety-boundary improvement.

**Commands:**
```bash
git status --short
git add src/oss_claimcheck/core.py src/oss_claimcheck/cli.py src/oss_claimcheck/safety.py tests/test_evidence_pack.py tests/test_safety.py README.md ROADMAP.md docs/security.md
git commit -m "add untrusted input safety boundaries"
git push origin main
```

**CI check:**
```bash
gh run list --repo smchu92/oss-claimcheck --limit 5
```

**Close issue:**
```bash
gh issue close 5 --repo smchu92/oss-claimcheck --comment 'Implemented untrusted input safety boundaries: strict repo parsing, URL scheme validation, output path guards, limited local source text reads, and security documentation.'
```

---

## Implementation Order

1. Repo parser tests → parser implementation.
2. Safety helper tests → safety helper implementation.
3. CLI integration tests → CLI wiring.
4. Docs/README/ROADMAP.
5. Full validation/build.
6. Commit/push/CI/issue close.

## Risk Notes

- Do not over-tighten GitHub owner/repo regex in a way that rejects real GitHub names with `.` or `-`.
- Avoid implementing network crawling while working on safety boundaries.
- Avoid writing tests that depend on absolute machine-specific paths except `/` and `Path.home()`.
- Keep max source text file size configurable by helper argument, but no new CLI config unless needed.
