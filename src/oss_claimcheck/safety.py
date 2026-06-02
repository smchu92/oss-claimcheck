from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


_ALLOWED_SOURCE_SCHEMES = {"http", "https"}
_DEFAULT_MAX_TEXT_BYTES = 200_000


def validate_source_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SOURCE_SCHEMES or not parsed.netloc:
        raise ValueError("source URL must use http or https and include a host")
    return url


def validate_output_dir(path: Path) -> Path:
    resolved = path.expanduser().resolve(strict=False)
    home = Path.home().resolve()
    cwd = Path.cwd().resolve()

    if resolved == Path(resolved.anchor) or resolved == home or resolved == cwd:
        raise ValueError("output directory must be a dedicated child directory, not a filesystem root, home, or current working directory")
    return resolved


def read_limited_text_file(path: Path, *, max_bytes: int = _DEFAULT_MAX_TEXT_BYTES) -> str:
    resolved = path.expanduser().resolve(strict=False)
    if not resolved.is_file():
        raise ValueError("official source text file must exist and be a regular file")
    if resolved.stat().st_size > max_bytes:
        raise ValueError(f"official source text file must be at most {max_bytes} bytes")
    return resolved.read_text(encoding="utf-8")
