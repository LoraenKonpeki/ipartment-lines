from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import subprocess
import sys

from ipartment_lines.lines import LineRecord
from ipartment_lines.mysql_export import render_mysql_sql
from ipartment_lines.search_db import encode_search_database


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--sample-interval-ms", type=int, default=2000)
    parser.add_argument("--min-confidence", type=float, default=0.75)
    parser.add_argument("--ffmpeg-threads", type=int, default=2)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    parts_dir = output_dir / "parts"
    parts_dir.mkdir(exist_ok=True)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = manifest["sources"]

    def run_source(source: dict) -> Path:
        page = int(source["page"])
        out_path = parts_dir / f"{page:02d}.json"
        done_path = parts_dir / f"{page:02d}.done"
        if out_path.exists() and done_path.exists():
            print(f"skip page {page:02d} {source['filename']}", flush=True)
            return out_path

        tmp_path = parts_dir / f"{page:02d}.json.tmp"
        command = [
            sys.executable,
            "-m",
            "ipartment_lines.cli",
            "extract-lines",
            "--manifest",
            str(manifest_path),
            "--output",
            str(tmp_path),
            "--only-source",
            source["filename"],
            "--sample-interval-ms",
            str(args.sample_interval_ms),
            "--min-confidence",
            str(args.min_confidence),
            "--ffmpeg-threads",
            str(args.ffmpeg_threads),
        ]
        print(f"start page {page:02d} {source['filename']}", flush=True)
        subprocess.run(command, check=True)
        tmp_path.replace(out_path)
        done_path.write_text("ok\n", encoding="utf-8")
        print(f"done page {page:02d} {source['filename']}", flush=True)
        return out_path

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_source, source): source for source in sources}
        for future in as_completed(futures):
            source = futures[future]
            try:
                future.result()
            except Exception as exc:
                print(f"failed {source['filename']}: {exc}", file=sys.stderr, flush=True)
                raise

    records = []
    for path in sorted(parts_dir.glob("*.json")):
        records.extend(json.loads(path.read_text(encoding="utf-8")))

    records.sort(key=lambda row: (row["season"], row["episode"], row["start_ms"], row["id"]))
    lines_path = output_dir / "lines.json"
    lines_path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    line_records = [LineRecord(**row) for row in records]
    sql_path = output_dir / "lines.sql"
    sql_path.write_text(render_mysql_sql(line_records), encoding="utf-8")

    db_path = output_dir / "lines_db.gz"
    db_path.write_bytes(encode_search_database(line_records))

    print(f"merged records={len(records)}", flush=True)
    print(lines_path, flush=True)
    print(sql_path, flush=True)
    print(db_path, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
