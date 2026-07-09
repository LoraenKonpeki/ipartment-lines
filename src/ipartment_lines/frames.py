from __future__ import annotations

from dataclasses import dataclass
from html import escape
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
    label: str = "sample"


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


def select_crop_samples(
    manifest: dict,
    *,
    offset_ms: int = 60_000,
    points: list[str] | None = None,
) -> list[CropSample]:
    samples: list[CropSample] = []
    sample_points = points or ["legacy"]
    for source in manifest.get("sources", []):
        crop = source["crop"]
        video_path = source["video_path"]
        for segment in source.get("segments", []):
            for point in sample_points:
                if point == "legacy":
                    sample_time = min(segment["start_ms"] + offset_ms, max(segment["start_ms"], segment["end_ms"] - 1))
                    filename = f"{segment['id']}_{sample_time:09d}.jpg"
                    label = f"start+{offset_ms // 1000}s"
                else:
                    sample_time = _resolve_point(point, segment["start_ms"], segment["end_ms"])
                    filename = f"{segment['id']}_{_safe_label(point)}_{sample_time:09d}.jpg"
                    label = point
                samples.append(
                    CropSample(
                        segment_id=segment["id"],
                        video_path=video_path,
                        time_ms=sample_time,
                        crop=crop,
                        filename=filename,
                        label=label,
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


def render_crop_gallery(samples: list[CropSample], *, manifest: dict) -> str:
    source_by_segment = {}
    for source in manifest.get("sources", []):
        for segment in source.get("segments", []):
            source_by_segment[segment["id"]] = source.get("filename", "")

    sections = []
    for segment_id in dict.fromkeys(sample.segment_id for sample in samples):
        segment_samples = [sample for sample in samples if sample.segment_id == segment_id]
        cards = "\n".join(
            (
                '<figure class="sample">'
                f'<img src="{escape(sample.filename)}" alt="{escape(segment_id)} {escape(sample.label)}">'
                f"<figcaption>{escape(sample.label)} · {_format_time(sample.time_ms)}</figcaption>"
                "</figure>"
            )
            for sample in segment_samples
        )
        sections.append(
            (
                '<section class="segment">'
                f"<h2>{escape(segment_id)}</h2>"
                f'<p class="source">{escape(source_by_segment.get(segment_id, ""))}</p>'
                f'<div class="grid">{cards}</div>'
                "</section>"
            )
        )

    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>ipartment-lines crop calibration</title>
  <style>
    body { margin: 24px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6f7f9; color: #15171a; }
    h1 { font-size: 24px; margin: 0 0 20px; }
    .segment { margin: 0 0 28px; padding-bottom: 24px; border-bottom: 1px solid #d7dbe0; }
    h2 { margin: 0; font-size: 18px; }
    .source { margin: 4px 0 12px; color: #606873; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 12px; }
    .sample { margin: 0; background: white; border: 1px solid #dfe3e8; }
    img { display: block; width: 100%; height: auto; }
    figcaption { padding: 8px 10px; font-size: 13px; color: #424851; }
  </style>
</head>
<body>
  <h1>Crop Calibration</h1>
  {sections}
</body>
</html>
""".replace("{sections}", "\n  ".join(sections))


def _resolve_point(point: str, start_ms: int, end_ms: int) -> int:
    latest = max(start_ms, end_ms - 1)
    if point == "mid":
        return start_ms + (end_ms - start_ms) // 2
    if point.startswith("start+"):
        return min(start_ms + _parse_seconds(point.removeprefix("start+")), latest)
    if point.startswith("end-"):
        return max(start_ms, end_ms - _parse_seconds(point.removeprefix("end-")))
    raise ValueError(f"Unsupported sample point: {point}")


def _parse_seconds(value: str) -> int:
    if not value.endswith("s"):
        raise ValueError(f"Sample point duration must end with s: {value}")
    return int(value[:-1]) * 1000


def _safe_label(label: str) -> str:
    return label.replace("+", "_").replace("-", "_")


def _format_time(time_ms: int) -> str:
    total_seconds = time_ms // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
