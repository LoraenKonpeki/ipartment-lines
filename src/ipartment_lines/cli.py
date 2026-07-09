from __future__ import annotations

import argparse
import json
from pathlib import Path

from .lines import LineRecord
from .manifest import build_manifest
from .search_db import encode_search_database


def main() -> None:
    parser = argparse.ArgumentParser(prog="ipartment-lines")
    subparsers = parser.add_subparsers(dest="command", required=True)

    manifest_parser = subparsers.add_parser("build-manifest")
    manifest_parser.add_argument("--parts", required=True, help="Path to Bilibili parts.tsv")
    manifest_parser.add_argument("--metadata", required=True, help="Path to Bilibili metadata.json")
    manifest_parser.add_argument("--video-root", required=True, help="Directory containing source videos")
    manifest_parser.add_argument("--output", required=True, help="Output manifest JSON path")

    db_parser = subparsers.add_parser("build-db")
    db_parser.add_argument("--lines", required=True, help="Line records JSON path")
    db_parser.add_argument("--output", required=True, help="Output gzip database path")

    args = parser.parse_args()
    if args.command == "build-manifest":
        parts_tsv = Path(args.parts).read_text(encoding="utf-8")
        metadata = json.loads(Path(args.metadata).read_text(encoding="utf-8"))
        manifest = build_manifest(
            parts_tsv=parts_tsv,
            metadata=metadata,
            video_root=args.video_root,
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif args.command == "build-db":
        raw_records = json.loads(Path(args.lines).read_text(encoding="utf-8"))
        records = [LineRecord(**record) for record in raw_records]
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encode_search_database(records))


if __name__ == "__main__":
    main()
