from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .core import prepare_evidence_pack, render_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="link-evidence-pack")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Generate an evidence pack from provided claim inputs.")
    prepare.add_argument("--url", required=True, help="Original source URL, e.g. X post, blog, repo, or docs page.")
    prepare.add_argument("--claim-text", required=True, help="Claim text copied from the source.")
    prepare.add_argument("--repo", help="Optional GitHub repository reference, e.g. owner/repo.")
    prepare.add_argument("--output-dir", required=True, help="Directory to write evidence.json and evidence.md.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "prepare":
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        pack = prepare_evidence_pack(url=args.url, claim_text=args.claim_text, repo=args.repo)
        (output_dir / "evidence.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n")
        (output_dir / "evidence.md").write_text(render_markdown(pack))
        print(f"Wrote {output_dir / 'evidence.json'}")
        print(f"Wrote {output_dir / 'evidence.md'}")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
