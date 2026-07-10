from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class ScreenshotJob:
    video_path: Path
    time_ms: int
    output_path: Path


def load_line_records(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_screenshot_jobs(
    records: list[dict],
    *,
    video_root: Path,
    output_root: Path,
) -> list[ScreenshotJob]:
    jobs: list[ScreenshotJob] = []
    for record in records:
        jobs.append(
            ScreenshotJob(
                video_path=video_root / record["source"],
                time_ms=int(record["start_ms"]),
                output_path=output_root / record["screenshot_key"],
            )
        )
    return jobs


def pending_jobs(jobs: list[ScreenshotJob]) -> list[ScreenshotJob]:
    return [job for job in jobs if not (job.output_path.exists() and job.output_path.stat().st_size > 0)]


def prepare_fresh_output_dir(output_dir: Path, *, archive_tag: str) -> Path | None:
    """Archive a populated output directory and recreate it for a full rebuild."""
    if output_dir.exists():
        if not output_dir.is_dir():
            raise ValueError(f"screenshot output path is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            archive_path = output_dir.with_name(f"{output_dir.name}.{archive_tag}")
            if archive_path.exists():
                raise FileExistsError(f"screenshot archive already exists: {archive_path}")
            output_dir.replace(archive_path)
            output_dir.mkdir(parents=True)
            return archive_path
    else:
        output_dir.mkdir(parents=True)
    return None


def build_ffmpeg_command(
    job: ScreenshotJob,
    *,
    width: int = 1280,
    quality: int = 80,
    output_path: Path | None = None,
) -> list[str]:
    target = output_path or job.output_path
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-ss",
        f"{job.time_ms / 1000:.3f}",
        "-i",
        str(job.video_path),
        "-frames:v",
        "1",
        "-vf",
        f"scale={width}:-2",
        "-c:v",
        "libwebp",
        "-quality",
        str(quality),
        str(target),
    ]


def generate_one(job: ScreenshotJob, *, width: int = 1280, quality: int = 80) -> Path:
    if job.output_path.exists() and job.output_path.stat().st_size > 0:
        return job.output_path

    job.output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = job.output_path.with_name(f".{job.output_path.name}.tmp.webp")
    command = build_ffmpeg_command(job, width=width, quality=quality, output_path=tmp_path)
    try:
        subprocess.run(command, check=True)
        tmp_path.replace(job.output_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return job.output_path


def generate_screenshots(
    jobs: list[ScreenshotJob],
    *,
    width: int = 1280,
    quality: int = 80,
    workers: int = 2,
    progress_every: int = 100,
) -> tuple[int, int]:
    todo = pending_jobs(jobs)
    total = len(todo)
    if total == 0:
        return (0, 0)

    completed = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(generate_one, job, width=width, quality=quality) for job in todo]
        for future in as_completed(futures):
            future.result()
            completed += 1
            if progress_every > 0 and (completed % progress_every == 0 or completed == total):
                print(f"generated {completed}/{total}", flush=True)
    return (completed, total)
