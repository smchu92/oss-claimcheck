from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .core import prepare_evidence_pack, render_markdown
from .safety import read_limited_text_file, validate_output_dir, validate_source_url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oss-claimcheck")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Generate an evidence pack from provided claim inputs.")
    prepare.add_argument("--url", required=True, help="Original source URL, e.g. X post, blog, repo, or docs page.")
    prepare.add_argument("--claim-text", required=True, help="Claim text copied from the source.")
    prepare.add_argument("--repo", help="Optional GitHub repository reference, e.g. owner/repo.")
    prepare.add_argument("--output-dir", required=True, help="Directory to write evidence.json and evidence.md.")
    prepare.add_argument("--fetch-github", action="store_true", help="Fetch live GitHub metadata for --repo.")
    prepare.add_argument("--official-source-title", help="Title for an official source used for quote extraction.")
    prepare.add_argument("--official-source-url", help="URL for an official source used for quote extraction.")
    prepare.add_argument("--official-source-text", help="Official source text to search for claim-supporting quotes.")
    prepare.add_argument("--official-source-text-file", help="File containing official source text to search for quotes.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "prepare":
        try:
            source_url = validate_source_url(args.url)
            output_dir = validate_output_dir(Path(args.output_dir))
        except ValueError as error:
            parser.error(str(error))
        output_dir.mkdir(parents=True, exist_ok=True)
        github_fetcher = None
        if args.fetch_github:
            from .github import fetch_github_repo_metadata
            github_fetcher = fetch_github_repo_metadata

        official_sources = []
        official_source_text = args.official_source_text
        if args.official_source_text_file:
            try:
                official_source_text = read_limited_text_file(Path(args.official_source_text_file))
            except ValueError as error:
                parser.error(str(error))
        if official_source_text:
            official_sources.append({
                "title": args.official_source_title or "Official source",
                "url": args.official_source_url,
                "text": official_source_text,
            })

        pack = prepare_evidence_pack(
            url=source_url,
            claim_text=args.claim_text,
            repo=args.repo,
            github_fetcher=github_fetcher,
            official_sources=official_sources,
        )
        (output_dir / "evidence.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n")
        (output_dir / "evidence.md").write_text(render_markdown(pack))
        print(f"Wrote {output_dir / 'evidence.json'}")
        print(f"Wrote {output_dir / 'evidence.md'}")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
