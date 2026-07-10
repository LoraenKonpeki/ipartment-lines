from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

from ipartment_lines.screenshots import prepare_fresh_output_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default="/root/GithubProjects/ipartment-lines")
    parser.add_argument("--final-dir", default="/root/GithubProjects/ipartment-lines/data/final_exact")
    parser.add_argument("--plugin-data-dir", default="/root/astrbot/data/plugins/my_memes/ipartment_lines")
    parser.add_argument("--video-root", default="/root/videos/bilibili/BV1xQ9ZBGEJ2")
    parser.add_argument("--screenshot-workers", type=int, default=3)
    parser.add_argument("--poll-seconds", type=int, default=300)
    args = parser.parse_args()

    project_root = Path(args.project_root)
    final_dir = Path(args.final_dir)
    plugin_data_dir = Path(args.plugin_data_dir)
    final_lines = final_dir / "lines.json"
    final_sql = final_dir / "lines.sql"
    final_db = final_dir / "lines_db.gz"

    while not (final_lines.exists() and final_sql.exists() and final_db.exists()):
        print("waiting for exact OCR final outputs", flush=True)
        time.sleep(args.poll_seconds)

    plugin_data_dir.mkdir(parents=True, exist_ok=True)
    target_lines = plugin_data_dir / "lines.json"
    if target_lines.exists():
        backup = plugin_data_dir / f"lines.before-exact-{int(time.time())}.json"
        shutil.copy2(target_lines, backup)
        print(f"backed up {target_lines} to {backup}", flush=True)

    shutil.copy2(final_lines, target_lines)
    print(f"published {final_lines} to {target_lines}", flush=True)

    screenshot_dir = plugin_data_dir / "screenshots_1280"
    screenshot_archive = prepare_fresh_output_dir(
        screenshot_dir,
        archive_tag=f"before-exact-{int(time.time())}",
    )
    if screenshot_archive is not None:
        print(f"archived previous screenshots to {screenshot_archive}", flush=True)

    command = [
        sys.executable,
        "-m",
        "ipartment_lines.cli",
        "generate-screenshots",
        "--lines",
        str(target_lines),
        "--video-root",
        args.video_root,
        "--output-dir",
        str(screenshot_dir),
        "--width",
        "1280",
        "--quality",
        "80",
        "--workers",
        str(args.screenshot_workers),
    ]
    subprocess.run(command, cwd=project_root, check=True)
    print("screenshots generated", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
