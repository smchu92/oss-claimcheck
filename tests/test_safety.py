from pathlib import Path

import pytest

from oss_claimcheck.safety import read_limited_text_file, validate_output_dir, validate_source_url


def test_validate_source_url_allows_http_and_https():
    assert validate_source_url("https://x.com/example/status/123") == "https://x.com/example/status/123"
    assert validate_source_url("http://example.com/post") == "http://example.com/post"


def test_validate_source_url_rejects_non_web_schemes():
    for value in ["file:///etc/passwd", "javascript:alert(1)", "", "https://"]:
        with pytest.raises(ValueError):
            validate_source_url(value)


def test_validate_output_dir_allows_nested_directory(tmp_path):
    output_dir = tmp_path / "evidence"

    assert validate_output_dir(output_dir) == output_dir.resolve()


def test_validate_output_dir_rejects_dangerous_roots(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    for value in [Path("/"), Path.home(), tmp_path]:
        with pytest.raises(ValueError):
            validate_output_dir(value)


def test_read_limited_text_file_reads_small_file(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("official source text")

    assert read_limited_text_file(source, max_bytes=100) == "official source text"


def test_read_limited_text_file_rejects_large_or_non_file(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("too large")

    with pytest.raises(ValueError):
        read_limited_text_file(source, max_bytes=3)

    with pytest.raises(ValueError):
        read_limited_text_file(tmp_path / "missing.txt", max_bytes=100)
