from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .core import RepoRef


def _request_json(url: str, *, timeout: float) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "oss-claimcheck/0.1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _request_json_or_none(url: str, *, timeout: float) -> Any | None:
    try:
        return _request_json(url, timeout=timeout)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def fetch_github_repo_metadata(repo: RepoRef, *, timeout: float = 10.0) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repo.owner}/{repo.name}"
    data = _request_json(url, timeout=timeout)

    license_info = data.get("license") or {}
    root_contents = _request_json_or_none(f"{url}/contents", timeout=timeout) or []
    root_names = {item.get("name", "").lower(): item.get("name", "") for item in root_contents if isinstance(item, dict)}
    package_files = [
        root_names[name]
        for name in ["pyproject.toml", "package.json", "cargo.toml", "go.mod", "setup.py"]
        if name in root_names
    ]
    readme_present = _request_json_or_none(f"{url}/readme", timeout=timeout) is not None
    releases = _request_json_or_none(f"{url}/releases?per_page=1", timeout=timeout) or []

    return {
        "description": data.get("description"),
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "open_issues": data.get("open_issues_count"),
        "default_branch": data.get("default_branch"),
        "license": license_info.get("spdx_id") if isinstance(license_info, dict) else None,
        "updated_at": data.get("updated_at"),
        "pushed_at": data.get("pushed_at"),
        "readme_present": readme_present,
        "package_files": package_files,
        "release_count": len(releases),
    }
