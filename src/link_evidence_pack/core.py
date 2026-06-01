from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass(frozen=True)
class RepoRef:
    owner: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def url(self) -> str:
        return f"https://github.com/{self.owner}/{self.name}"


def parse_repo_ref(repo: str) -> RepoRef:
    normalized = repo.strip().removeprefix("https://github.com/").strip("/")
    parts = normalized.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError("repo must be an owner/name pair or GitHub URL")
    return RepoRef(owner=parts[0], name=parts[1])


def detect_hype_signals(text: str) -> list[str]:
    lowered = text.lower()
    phrases = [
        "works everywhere",
        "does phd work in seconds",
        "replaces all reviewers",
        "fully autonomous",
        "no limits",
        "zero setup",
        "magic",
    ]
    return [phrase for phrase in phrases if phrase in lowered]


def prepare_evidence_pack(
    *,
    url: str,
    claim_text: str,
    repo: str | None = None,
    github_fetcher: Callable[[RepoRef], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    repo_ref = parse_repo_ref(repo) if repo else None
    now = datetime.now(timezone.utc).isoformat()

    confirmed: list[str] = []
    repository = None
    if repo_ref:
        repository = {
            "full_name": repo_ref.full_name,
            "owner": repo_ref.owner,
            "name": repo_ref.name,
            "url": repo_ref.url,
            "verification_status": "identity hint only; live GitHub metadata not fetched yet",
        }
        if github_fetcher:
            metadata = github_fetcher(repo_ref)
            repository.update(metadata)
            repository["verification_status"] = "github metadata fetched"
            confirmed.append(f"GitHub metadata fetched for {repo_ref.full_name}")

    unverified = [
        "source text was provided by the user and still needs official-source verification",
        "README/package/license claims have not been checked yet",
    ]
    if not github_fetcher:
        unverified.insert(1, "repository metadata has not been fetched from GitHub yet")

    return {
        "generated_at": now,
        "source": {
            "url": url,
            "type": "user-provided-url",
        },
        "claim": {
            "text": claim_text,
        },
        "repository": repository,
        "verification_checklist": [
            "official repository exists",
            "README supports the claim",
            "license is present and compatible",
            "package/install path exists",
            "recent maintainer activity is visible",
            "security or destructive behavior is documented",
        ],
        "status": {
            "confirmed": confirmed,
            "unverified": unverified,
            "hype_signals": detect_hype_signals(claim_text),
        },
        "follow_up_questions": [
            "What official docs or README sections support the claim?",
            "Does the repo contain an installable package or only a demo?",
            "Is the license present and compatible with OSS adoption?",
            "What is confirmed by code versus marketing copy?",
            "What should a maintainer smoke-test before adopting this tool?",
        ],
    }


def _bullet_list(items: list[str], empty: str = "None yet.") -> str:
    if not items:
        return empty
    return "\n".join(f"- {item}" for item in items)


def render_markdown(pack: dict[str, Any]) -> str:
    repo = pack.get("repository")
    repo_section = "Not provided."
    if repo:
        metadata_lines = [
            f"- Full name: `{repo['full_name']}`",
            f"- URL: {repo['url']}",
            f"- Status: {repo['verification_status']}",
        ]
        for key, label in [
            ("description", "Description"),
            ("stars", "Stars"),
            ("forks", "Forks"),
            ("open_issues", "Open issues"),
            ("default_branch", "Default branch"),
            ("license", "License"),
            ("updated_at", "Updated at"),
            ("pushed_at", "Pushed at"),
        ]:
            if repo.get(key) is not None:
                metadata_lines.append(f"- {label}: {repo[key]}")
        repo_section = "\n".join(metadata_lines)

    status = pack["status"]
    return f"""# Evidence Pack

Generated: {pack['generated_at']}

## Source

- URL: {pack['source']['url']}
- Type: {pack['source']['type']}

## Claim

{pack['claim']['text']}

## Repository

{repo_section}

## Confirmed

{_bullet_list(status['confirmed'])}

## Unverified

{_bullet_list(status['unverified'])}

## Hype signals

{_bullet_list(status['hype_signals'])}

## Verification checklist

{_bullet_list(pack['verification_checklist'])}

## Follow-up questions

{_bullet_list(pack['follow_up_questions'])}
"""
