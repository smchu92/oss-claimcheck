from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
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


def _claim_keywords(text: str) -> set[str]:
    stopwords = {
        "about", "after", "before", "claim", "does", "from", "into", "manual",
        "that", "this", "tool", "with", "without", "review", "reviews", "source",
        "official", "packs", "pack", "oss",
    }
    return {
        word
        for word in re.findall(r"[a-z0-9][a-z0-9-]{2,}", text.lower())
        if word not in stopwords
    }


def extract_official_source_quotes(source_text: str, claim_text: str, *, max_quotes: int = 3) -> list[str]:
    keywords = _claim_keywords(claim_text)
    if not keywords:
        return []

    text_without_code = re.sub(r"```.*?```", " ", source_text, flags=re.DOTALL)
    candidates = [part.strip(" -#\t") for part in re.split(r"(?<=[.!?])\s+|\n+", text_without_code) if part.strip()]
    scored: list[tuple[int, int, str]] = []
    for index, sentence in enumerate(candidates):
        if len(sentence) > 280:
            continue
        sentence_keywords = _claim_keywords(sentence)
        overlap = len(keywords & sentence_keywords)
        if overlap:
            scored.append((overlap, -index, sentence))

    scored.sort(reverse=True)
    return [sentence for _, _, sentence in scored[:max_quotes]]


def _repository_signals(repository: dict[str, Any]) -> dict[str, Any]:
    package_files = repository.get("package_files") or []
    license_value = repository.get("license")
    return {
        "readme_present": bool(repository.get("readme_present")),
        "license_present": bool(license_value and license_value != "NOASSERTION"),
        "package_files": package_files,
        "release_count": repository.get("release_count"),
    }


def _confirmed_repository_signals(repository: dict[str, Any]) -> list[str]:
    signals = repository.get("signals") or {}
    confirmed = []
    if signals.get("readme_present"):
        confirmed.append("README detected")
    if signals.get("license_present"):
        confirmed.append(f"License detected: {repository.get('license')}")
    if signals.get("package_files"):
        confirmed.append(f"Package metadata detected: {', '.join(signals['package_files'])}")
    if signals.get("release_count"):
        confirmed.append(f"GitHub releases detected: {signals['release_count']}")
    return confirmed


def prepare_evidence_pack(
    *,
    url: str,
    claim_text: str,
    repo: str | None = None,
    github_fetcher: Callable[[RepoRef], dict[str, Any]] | None = None,
    official_sources: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    repo_ref = parse_repo_ref(repo) if repo else None
    now = datetime.now(timezone.utc).isoformat()

    confirmed: list[str] = []
    repository: dict[str, Any] | None = None
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
            repository["signals"] = _repository_signals(repository)
            confirmed.append(f"GitHub metadata fetched for {repo_ref.full_name}")
            confirmed.extend(_confirmed_repository_signals(repository))

    official_source_entries = []
    for source in official_sources or []:
        text = source.get("text", "")
        entry = {
            "title": source.get("title") or "Official source",
            "url": source.get("url"),
            "quotes": extract_official_source_quotes(text, claim_text),
        }
        official_source_entries.append(entry)
        if entry["quotes"]:
            confirmed.append(f"Official source quotes extracted from {entry['title']}")
    unverified = [
        "source text was provided by the user and still needs official-source verification",
    ]
    if not repository or not repository.get("signals"):
        unverified.append("README/package/license claims have not been checked yet")
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
        "official_sources": official_source_entries,
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


def _official_sources_markdown(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return "None provided."

    sections = []
    for source in sources:
        header = f"### {source['title']}"
        if source.get("url"):
            header += f"\n\n- URL: {source['url']}"
        quotes = source.get("quotes") or []
        quote_lines = "\n".join(f"- \"{quote}\"" for quote in quotes) if quotes else "- No matching quote found."
        sections.append(f"{header}\n\n{quote_lines}")
    return "\n\n".join(sections)


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
    official_sources = _official_sources_markdown(pack.get("official_sources", []))
    return f"""# Evidence Pack

Generated: {pack['generated_at']}

## Source

- URL: {pack['source']['url']}
- Type: {pack['source']['type']}

## Claim

{pack['claim']['text']}

## Repository

{repo_section}

## Official source quotes

{official_sources}

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
