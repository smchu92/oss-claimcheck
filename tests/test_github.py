import json

from oss_claimcheck.core import RepoRef
from oss_claimcheck.github import fetch_github_repo_metadata


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_fetch_github_repo_metadata_parses_deterministic_api_fixtures(monkeypatch):
    fixtures = {
        "https://api.github.com/repos/owner/repo": {
            "description": "Adoption evidence generator",
            "stargazers_count": 42,
            "forks_count": 7,
            "open_issues_count": 3,
            "default_branch": "main",
            "license": {"spdx_id": "MIT"},
            "updated_at": "2026-06-01T00:00:00Z",
            "pushed_at": "2026-06-02T00:00:00Z",
            "archived": False,
            "disabled": False,
        },
        "https://api.github.com/repos/owner/repo/contents": [
            {"name": "README.md"},
            {"name": "pyproject.toml"},
            {"name": "package.json"},
            {"name": "src"},
        ],
        "https://api.github.com/repos/owner/repo/readme": {"name": "README.md"},
        "https://api.github.com/repos/owner/repo/releases?per_page=1": [
            {"tag_name": "v1.0.0"},
        ],
    }
    requested_urls = []

    def fake_urlopen(request, timeout):
        requested_urls.append(request.full_url)
        assert timeout == 2.5
        return FakeResponse(fixtures[request.full_url])

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    metadata = fetch_github_repo_metadata(RepoRef("owner", "repo"), timeout=2.5)

    assert requested_urls == list(fixtures)
    assert metadata == {
        "description": "Adoption evidence generator",
        "stars": 42,
        "forks": 7,
        "open_issues": 3,
        "default_branch": "main",
        "license": "MIT",
        "updated_at": "2026-06-01T00:00:00Z",
        "pushed_at": "2026-06-02T00:00:00Z",
        "archived": False,
        "disabled": False,
        "readme_present": True,
        "package_files": ["pyproject.toml", "package.json"],
        "release_count": 1,
    }


def test_fetch_github_repo_metadata_uses_current_user_agent(monkeypatch):
    captured_user_agents = []

    def fake_urlopen(request, timeout):
        captured_user_agents.append(request.headers["User-agent"])
        if request.full_url.endswith("/contents"):
            return FakeResponse([])
        if request.full_url.endswith("/readme"):
            return FakeResponse({})
        if request.full_url.endswith("/releases?per_page=1"):
            return FakeResponse([])
        return FakeResponse({"license": None})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    fetch_github_repo_metadata(RepoRef("owner", "repo"))

    assert set(captured_user_agents) == {"oss-claimcheck/0.1.1"}
