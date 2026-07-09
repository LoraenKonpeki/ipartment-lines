from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any, Callable, Iterable, Optional, Tuple

from .lines import LineRecord, OcrRead, merge_ocr_reads


OcrFunction = Callable[[Any], Tuple[Optional[str], float]]


def iter_sample_times(start_ms: int, end_ms: int, interval_ms: int) -> Iterable[int]:
    current = start_ms
    while current < end_ms:
        yield current
        current += interval_ms


def pick_recognition_region(crop: dict[str, int], *, season: int | None = None) -> dict[str, int]:
    if season in (2, 3):
        return {
            "x": int(crop["w"] * 0.0333),
            "y": int(crop["h"] * 0.3478),
            "w": int(crop["w"] * 0.9333),
            "h": int(crop["h"] * 0.6304),
        }

    return {
        "x": int(crop["w"] * 0.0667),
        "y": int(crop["h"] * 0.1522),
        "w": int(crop["w"] * 0.8667),
        "h": int(crop["h"] * 0.7392),
    }


def extract_manifest_lines(
    manifest: dict,
    *,
    output_path: Path,
    ocr: OcrFunction,
    sample_interval_ms: int = 1000,
    min_confidence: float = 0.75,
    limit_segments: int | None = None,
    only_segment: str | None = None,
    only_source: str | None = None,
    max_samples_per_segment: int | None = None,
    ffmpeg_threads: int = 2,
) -> list[LineRecord]:
    records: list[LineRecord] = []
    processed_segments = 0

    for source in manifest.get("sources", []):
        if only_source and source["filename"] != only_source:
            continue
        video_path = source["video_path"]
        crop = source["crop"]
        rec_region = pick_recognition_region(crop, season=source.get("season"))

        for segment in source.get("segments", []):
            if only_segment and segment["id"] != only_segment:
                continue
            if limit_segments is not None and processed_segments >= limit_segments:
                _write_records(output_path, records)
                return records

            reads = _extract_segment_reads(
                video_path=video_path,
                crop=crop,
                rec_region=rec_region,
                segment=segment,
                ocr=ocr,
                sample_interval_ms=sample_interval_ms,
                min_confidence=min_confidence,
                max_samples=max_samples_per_segment,
                ffmpeg_threads=ffmpeg_threads,
            )
            records.extend(
                merge_ocr_reads(
                    season=segment["season"],
                    episode=segment["episode"],
                    source=source["filename"],
                    reads=reads,
                    sample_interval_ms=sample_interval_ms,
                )
            )
            processed_segments += 1
            _write_records(output_path, records)

    return records


def _extract_segment_reads(
    *,
    video_path: str,
    crop: dict[str, int],
    rec_region: dict[str, int],
    segment: dict,
    ocr: OcrFunction,
    sample_interval_ms: int,
    min_confidence: float,
    max_samples: int | None = None,
    ffmpeg_threads: int = 2,
) -> list[OcrRead]:
    width = crop["w"]
    height = crop["h"]
    duration = (segment["end_ms"] - segment["start_ms"]) / 1000
    fps = 1000 / sample_interval_ms
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-threads",
        str(ffmpeg_threads),
        "-ss",
        f"{segment['start_ms'] / 1000:.3f}",
        "-t",
        f"{duration:.3f}",
        "-i",
        video_path,
        "-vf",
        f"fps={fps:.6f},crop={width}:{height}:{crop['x']}:{crop['y']}",
        "-pix_fmt",
        "bgr24",
        "-f",
        "rawvideo",
        "pipe:1",
    ]
    frame_size = width * height * 3
    reads: list[OcrRead] = []
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    assert process.stdout is not None
    stopped_early = False

    try:
        for index, time_ms in enumerate(iter_sample_times(segment["start_ms"], segment["end_ms"], sample_interval_ms)):
            if max_samples is not None and index >= max_samples:
                stopped_early = True
                break
            raw = process.stdout.read(frame_size)
            if len(raw) < frame_size:
                break
            import numpy as np

            frame = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
            region = frame[
                rec_region["y"] : rec_region["y"] + rec_region["h"],
                rec_region["x"] : rec_region["x"] + rec_region["w"],
            ]
            text, confidence = ocr(region)
            if text and confidence >= min_confidence:
                reads.append(
                    OcrRead(
                        time_ms=time_ms,
                        text=text,
                        screenshot_key=f"{segment['id']}/{time_ms:09d}.webp",
                    )
                )
    finally:
        if stopped_early:
            process.terminate()
        process.stdout.close()
        process.wait()
        if process.returncode not in (0, None) and not stopped_early:
            raise RuntimeError(f"ffmpeg failed for {segment['id']} with exit code {process.returncode}")

    return reads


def build_rapidocr_recognizer() -> OcrFunction:
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR(use_det=False, use_cls=False)

    def recognize(image: Any) -> tuple[str | None, float]:
        result, _ = engine(image)
        if not result:
            return None, 0.0
        text, score = result[0]
        return str(text), float(score)

    return recognize


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_records(path: Path, records: list[LineRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([record.__dict__ for record in records], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
