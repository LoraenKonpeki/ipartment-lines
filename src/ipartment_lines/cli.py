from __future__ import annotations

import argparse
import json
from pathlib import Path

from .extract import build_rapidocr_recognizer, extract_manifest_lines, load_manifest
from .frames import render_crop_gallery, select_crop_samples, write_crop_sample
from .lines import LineRecord
from .manifest import build_manifest
from .mysql_export import render_mysql_sql
from .search_db import encode_search_database
from .screenshots import build_screenshot_jobs, generate_screenshots, load_line_records


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

    extract_parser = subparsers.add_parser("extract-lines")
    extract_parser.add_argument("--manifest", required=True, help="Manifest JSON path")
    extract_parser.add_argument("--output", required=True, help="Output line records JSON path")
    extract_parser.add_argument("--sample-interval-ms", type=int, default=1000)
    extract_parser.add_argument("--min-confidence", type=float, default=0.75)
    extract_parser.add_argument("--limit-segments", type=int, default=None)
    extract_parser.add_argument("--only-segment", default=None)
    extract_parser.add_argument("--only-source", default=None)
    extract_parser.add_argument("--max-samples-per-segment", type=int, default=None)
    extract_parser.add_argument("--ffmpeg-threads", type=int, default=2)
    extract_parser.add_argument("--sample-frame-rate", type=float, default=24.0)
    extract_parser.add_argument(
        "--sampling-mode",
        choices=["exact-seek", "frame-select"],
        default="exact-seek",
    )

    sql_parser = subparsers.add_parser("export-mysql-sql")
    sql_parser.add_argument("--lines", required=True, help="Line records JSON path")
    sql_parser.add_argument("--output", required=True, help="Output SQL path")
    sql_parser.add_argument("--database", default="ipartment_lines")

    crop_parser = subparsers.add_parser("sample-crops")
    crop_parser.add_argument("--manifest", required=True, help="Manifest JSON path")
    crop_parser.add_argument("--output-dir", required=True, help="Directory for crop images")
    crop_parser.add_argument("--offset-ms", type=int, default=60_000, help="Offset after each segment start")
    crop_parser.add_argument(
        "--points",
        default=None,
        help="Comma-separated points such as start+60s,mid,end-60s. Overrides --offset-ms.",
    )
    crop_parser.add_argument("--gallery", default=None, help="Optional HTML gallery output path")
    crop_parser.add_argument("--limit", type=int, default=None, help="Maximum samples to extract")
    crop_parser.add_argument("--ssh-host", default=None, help="Run ffmpeg on this SSH host and scp results back")

    screenshots_parser = subparsers.add_parser("generate-screenshots")
    screenshots_parser.add_argument("--lines", required=True, help="Line records JSON path")
    screenshots_parser.add_argument("--video-root", required=True, help="Directory containing source videos")
    screenshots_parser.add_argument("--output-dir", required=True, help="Output screenshot directory")
    screenshots_parser.add_argument("--width", type=int, default=1280)
    screenshots_parser.add_argument("--quality", type=int, default=80)
    screenshots_parser.add_argument("--workers", type=int, default=2)
    screenshots_parser.add_argument("--limit", type=int, default=None, help="Maximum pending screenshots to generate")

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
    elif args.command == "extract-lines":
        manifest = load_manifest(Path(args.manifest))
        ocr = build_rapidocr_recognizer()
        extract_manifest_lines(
            manifest,
            output_path=Path(args.output),
            ocr=ocr,
            sample_interval_ms=args.sample_interval_ms,
            min_confidence=args.min_confidence,
            limit_segments=args.limit_segments,
            only_segment=args.only_segment,
            only_source=args.only_source,
            max_samples_per_segment=args.max_samples_per_segment,
            ffmpeg_threads=args.ffmpeg_threads,
            sample_frame_rate=args.sample_frame_rate,
            sampling_mode=args.sampling_mode,
        )
    elif args.command == "export-mysql-sql":
        raw_records = json.loads(Path(args.lines).read_text(encoding="utf-8"))
        records = [LineRecord(**record) for record in raw_records]
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_mysql_sql(records, database=args.database), encoding="utf-8")
    elif args.command == "sample-crops":
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        points = args.points.split(",") if args.points else None
        samples = select_crop_samples(manifest, offset_ms=args.offset_ms, points=points)
        if args.limit is not None:
            samples = samples[: args.limit]
        output_dir = Path(args.output_dir)
        for sample in samples:
            output_path = write_crop_sample(sample, output_dir, ssh_host=args.ssh_host)
            print(output_path)
        if args.gallery:
            gallery_path = Path(args.gallery)
            gallery_path.parent.mkdir(parents=True, exist_ok=True)
            gallery_path.write_text(render_crop_gallery(samples, manifest=manifest), encoding="utf-8")
    elif args.command == "generate-screenshots":
        records = load_line_records(Path(args.lines))
        jobs = build_screenshot_jobs(
            records,
            video_root=Path(args.video_root),
            output_root=Path(args.output_dir),
        )
        if args.limit is not None:
            jobs = jobs[: args.limit]
        generated, total = generate_screenshots(
            jobs,
            width=args.width,
            quality=args.quality,
            workers=args.workers,
        )
        print(f"generated {generated}/{total}")


if __name__ == "__main__":
    main()
