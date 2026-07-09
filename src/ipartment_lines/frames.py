from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess


@dataclass(frozen=True)
class CropSample:
    segment_id: str
    video_path: str
    time_ms: int
    crop: dict[str, int]
    filename: str


def build_ffmpeg_crop_command(
    *,
    video_path: str,
    time_ms: int,
    crop: dict[str, int],
    output_path: Path,
) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{time_ms / 1000:.3f}",
        "-i",
        video_path,
        "-frames:v",
        "1",
        "-vf",
        f"crop={crop['w']}:{crop['h']}:{crop['x']}:{crop['y']}",
        "-q:v",
        "2",
        str(output_path),
    ]


def select_crop_samples(manifest: dict, *, offset_ms: int = 60_000) -> list[CropSample]:
    samples: list[CropSample] = []
    for source in manifest.get("sources", []):
        crop = source["crop"]
        video_path = source["video_path"]
        for segment in source.get("segments", []):
            sample_time = min(segment["start_ms"] + offset_ms, max(segment["start_ms"], segment["end_ms"] - 1))
            samples.append(
                CropSample(
                    segment_id=segment["id"],
                    video_path=video_path,
                    time_ms=sample_time,
                    crop=crop,
                    filename=f"{segment['id']}_{sample_time:09d}.jpg",
                )
            )
    return samples


def write_crop_sample(sample: CropSample, output_dir: Path, *, ssh_host: str | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / sample.filename

    if ssh_host:
        remote_dir = f"/tmp/ipartment-lines-crops-{_shell_safe_segment(sample.segment_id)}"
        remote_path = f"{remote_dir}/{sample.filename}"
        remote_command = "mkdir -p {dir} && {ffmpeg}".format(
            dir=shlex.quote(remote_dir),
            ffmpeg=" ".join(
                shlex.quote(part)
                for part in build_ffmpeg_crop_command(
                    video_path=sample.video_path,
                    time_ms=sample.time_ms,
                    crop=sample.crop,
                    output_path=Path(remote_path),
                )
            ),
        )
        subprocess.run(["ssh", ssh_host, remote_command], check=True)
        subprocess.run(["scp", f"{ssh_host}:{remote_path}", str(output_path)], check=True)
        return output_path

    command = build_ffmpeg_crop_command(
        video_path=sample.video_path,
        time_ms=sample.time_ms,
        crop=sample.crop,
        output_path=output_path,
    )
    subprocess.run(command, check=True)
    return output_path


def _shell_safe_segment(segment_id: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in segment_id)
