from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Callable
from urllib.parse import urlparse


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


_REPO_PART_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def _valid_repo_part(value: str) -> bool:
    return bool(_REPO_PART_PATTERN.fullmatch(value)) and value not in {".", ".."}


def parse_repo_ref(repo: str) -> RepoRef:
    value = repo.strip()
    if value.startswith(("http://", "https://")):
        parsed = urlparse(value)
        if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
            raise ValueError("repo must be an owner/name pair or GitHub URL")
        normalized = parsed.path.strip("/")
    else:
        normalized = value.strip("/")

    parts = normalized.split("/")
    if len(parts) != 2 or not all(_valid_repo_part(part) for part in parts):
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


def _score_component(score: int, reasons: list[str]) -> dict[str, Any]:
    return {"score": max(0, min(100, score)), "reasons": reasons}


def _risk_level(score: int) -> str:
    if score >= 75:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def generate_evidence_score(
    *,
    repository: dict[str, Any] | None,
    official_sources: list[dict[str, Any]],
    hype_signals: list[str],
) -> dict[str, Any]:
    """Return deterministic heuristic evidence scores for maintainer triage."""
    signals = repository.get("signals") if repository else None
    signals = signals or {}
    identity_score = 0
    identity_reasons = []
    if repository:
        identity_score += 15
        identity_reasons.append(f"repository reference present: {repository['full_name']}")
    if repository and repository.get("verification_status") == "github metadata fetched":
        identity_score += 25
        identity_reasons.append("GitHub metadata fetched")
    if signals.get("readme_present"):
        identity_score += 20
        identity_reasons.append("README detected")
    if signals.get("license_present"):
        identity_score += 15
        license_value = repository.get("license") if repository else "unknown"
        identity_reasons.append(f"license detected: {license_value}")
    if any(source.get("quotes") for source in official_sources):
        identity_score += 25
        identity_reasons.append("official-source quote matched the claim")
    if not identity_reasons:
        identity_reasons.append("no repository or official-source identity evidence yet")

    maintenance_score = 0
    maintenance_reasons = []
    if repository and repository.get("verification_status") == "github metadata fetched":
        maintenance_score += 25
        maintenance_reasons.append("GitHub metadata available for maintenance checks")
    if signals.get("readme_present"):
        maintenance_score += 15
        maintenance_reasons.append("README gives maintainers a review surface")
    if signals.get("package_files"):
        maintenance_score += 20
        maintenance_reasons.append("package metadata detected: " + ", ".join(signals["package_files"]))
    if signals.get("release_count"):
        maintenance_score += 20
        maintenance_reasons.append(f"GitHub releases detected: {signals['release_count']}")
    if repository and (repository.get("pushed_at") or repository.get("updated_at")):
        maintenance_score += 20
        maintenance_reasons.append("repository has update timestamps")
    if not maintenance_reasons:
        maintenance_reasons.append("metadata needed for maintenance confidence has not been fetched")

    security_score = 0
    security_reasons = []
    if signals.get("license_present"):
        security_score += 30
        security_reasons.append("license is present")
    if signals.get("package_files"):
        security_score += 20
        security_reasons.append("package metadata gives dependency/install context")
    if signals.get("readme_present"):
        security_score += 15
        security_reasons.append("README can document setup and safety boundaries")
    if repository and repository.get("verification_status") == "github metadata fetched":
        security_score += 10
        security_reasons.append("repository identity was checked against GitHub metadata")
    if not security_reasons:
        security_reasons.append("no license/package/security-adjacent metadata confirmed yet")

    hype_score = min(100, len(hype_signals) * 25)
    hype_reasons = [f"hype signal detected: {signal}" for signal in hype_signals]
    if not hype_reasons:
        hype_reasons.append("no configured hype phrases detected in the claim text")

    components = {
        "identity": _score_component(identity_score, identity_reasons),
        "maintenance": _score_component(maintenance_score, maintenance_reasons),
        "security": _score_component(security_score, security_reasons),
        "hype_risk": {
            **_score_component(hype_score, hype_reasons),
            "risk_level": _risk_level(hype_score),
        },
    }
    overall = round(
        (
            components["identity"]["score"]
            + components["maintenance"]["score"]
            + components["security"]["score"]
            + (100 - components["hype_risk"]["score"])
        ) / 4
    )
    return {
        "overall": overall,
        "components": components,
        "note": "Heuristic evidence score only; not a security audit.",
    }


def _codex_prompt_references(confirmed: list[str], unverified: list[str], hype_signals: list[str]) -> str:
    references = []
    if confirmed:
        references.append("confirmed: " + "; ".join(confirmed[:3]))
    if unverified:
        references.append("unverified: " + "; ".join(unverified[:3]))
    if hype_signals:
        references.append("hype signals: " + "; ".join(hype_signals))
    return " | ".join(references) if references else "no specific evidence signals yet"


def generate_codex_smoke_test_prompts(
    *,
    claim_text: str,
    repository: dict[str, Any] | None,
    confirmed: list[str],
    unverified: list[str],
    hype_signals: list[str],
) -> list[dict[str, Any]]:
    repo_label = repository["full_name"] if repository else "the target repository"
    repo_url = repository["url"] if repository else "the repository URL from the evidence pack"
    references = _codex_prompt_references(confirmed, unverified, hype_signals)
    base_context = (
        f"Use only the repository at {repo_url} and the claim text below. "
        "Treat this as a smoke test, not a full audit. "
        f"Claim: {claim_text!r}. Evidence references: {references}."
    )
    prompts = [
        (
            "installation",
            f"{base_context} Check whether {repo_label} has a documented install path. Run the smallest safe install or dry-run command available, then report the exact commands, outputs, and any missing prerequisites.",
        ),
        (
            "basic run",
            f"{base_context} Find the quickest documented example or CLI entry point for {repo_label}. Execute the smallest non-destructive run, capture stdout/stderr, and say whether it supports the claim or only demonstrates a narrower behavior.",
        ),
        (
            "license check",
            f"{base_context} Verify the license for {repo_label} from repository files or GitHub metadata. Report the detected license, missing/ambiguous license evidence, and whether adoption needs human review.",
        ),
        (
            "failure-mode review",
            f"{base_context} Review likely failure modes before adoption: setup assumptions, network/API dependencies, destructive behavior, and exaggerated claims such as {', '.join(hype_signals) if hype_signals else 'unverified marketing claims'}. Return concrete risks and one safe follow-up test for each.",
        ),
    ]
    return [
        {
            "category": category,
            "suggested": True,
            "references": references,
            "prompt": prompt,
        }
        for category, prompt in prompts
    ]


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

    hype_signals = detect_hype_signals(claim_text)
    evidence_score = generate_evidence_score(
        repository=repository,
        official_sources=official_source_entries,
        hype_signals=hype_signals,
    )
    codex_prompts = generate_codex_smoke_test_prompts(
        claim_text=claim_text,
        repository=repository,
        confirmed=confirmed,
        unverified=unverified,
        hype_signals=hype_signals,
    )

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
            "hype_signals": hype_signals,
        },
        "evidence_score": evidence_score,
        "codex_smoke_test_prompts": codex_prompts,
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


def _codex_prompts_markdown(prompts: list[dict[str, Any]]) -> str:
    if not prompts:
        return "None generated."

    sections = []
    for prompt in prompts:
        sections.append(
            f"### {prompt['category'].title()}\n\n"
            "- Status: Suggested — verify before relying on this task\n"
            f"- References: {prompt['references']}\n\n"
            f"```text\n{prompt['prompt']}\n```"
        )
    return "\n\n".join(sections)


def _evidence_score_markdown(score: dict[str, Any]) -> str:
    components = score.get("components", {})
    lines = [
        f"- Overall: {score.get('overall')}/100",
        f"- Note: {score.get('note')}",
    ]
    for key, label in [
        ("identity", "Identity"),
        ("maintenance", "Maintenance"),
        ("security", "Security"),
        ("hype_risk", "Hype risk"),
    ]:
        component = components.get(key, {})
        detail = f"- {label}: {component.get('score')}/100"
        if key == "hype_risk" and component.get("risk_level"):
            detail += f" ({component['risk_level']} risk)"
        reasons = component.get("reasons") or []
        if reasons:
            detail += f" — {reasons[0]}"
        lines.append(detail)
    return "\n".join(lines)


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
    evidence_score = _evidence_score_markdown(pack["evidence_score"])
    codex_prompts = _codex_prompts_markdown(pack.get("codex_smoke_test_prompts", []))
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

## Evidence score

{evidence_score}

## Verification checklist

{_bullet_list(pack['verification_checklist'])}

## Codex-ready follow-up prompts

{codex_prompts}

## Follow-up questions

{_bullet_list(pack['follow_up_questions'])}
"""
