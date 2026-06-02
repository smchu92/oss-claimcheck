# Security and Untrusted Input Boundaries

`oss-claimcheck` processes third-party claims, URLs, repository metadata, and user-provided source text. Treat all of that content as untrusted.

## Current safety boundaries

- Source URLs must use `http://` or `https://` and include a host.
- GitHub repository references must be either `owner/repo` or `https://github.com/owner/repo`.
- Repository owner/name parts may contain only letters, numbers, `_`, `.`, and `-`; traversal segments such as `.` and `..` are rejected.
- `--fetch-github` only calls GitHub API endpoints derived from a validated GitHub repository reference.
- Official source text is provided by the user directly or through a local text file; arbitrary page crawling is not enabled by default.
- Local official-source text files must exist, be regular files, and stay under the default size limit.
- Output directories must be dedicated child directories; filesystem root, the user's home directory, and the current working directory are rejected.

## Non-goals for the current version

- No automatic `safe` / `unsafe` verdict.
- No arbitrary web crawling.
- No execution of repository code or source snippets.
- No dependency vulnerability scanning yet.

## Future network-fetching rules

Any future source-fetching feature should keep these constraints:

1. Require explicit user opt-in.
2. Use domain allowlists or clearly bounded fetch targets.
3. Enforce request timeouts and maximum response sizes.
4. Never execute fetched content.
5. Preserve evidence of what was fetched and what remains unverified.
6. Keep generated reports clear about confirmed facts versus inferred risk.

## Reporting security issues

This project is early-stage. If a safety boundary is missing or too permissive, open an issue with:

- the exact input
- expected behavior
- actual behavior
- why the input is risky
