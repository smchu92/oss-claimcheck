from __future__ import annotations

import json
import urllib.request
from typing import Any

from .core import RepoRef


def fetch_github_repo_metadata(repo: RepoRef, *, timeout: float = 10.0) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repo.owner}/{repo.name}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "link-evidence-pack/0.1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))

    license_info = data.get("license") or {}
    return {
        "description": data.get("description"),
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "open_issues": data.get("open_issues_count"),
        "default_branch": data.get("default_branch"),
        "license": license_info.get("spdx_id") if isinstance(license_info, dict) else None,
        "updated_at": data.get("updated_at"),
        "pushed_at": data.get("pushed_at"),
    }
