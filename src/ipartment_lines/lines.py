from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class OcrRead:
    time_ms: int
    text: str
    screenshot_key: str


@dataclass(frozen=True)
class LineRecord:
    id: str
    season: int
    episode: int
    source: str
    start_ms: int
    end_ms: int
    text: str
    screenshot_key: str


def clean_ocr_text(text: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
    if not cleaned:
        return None

    noise_patterns = (
        "关注不迷路",
        "补档",
        "IP江西",
        "跳转至",
        "哔哩哔哩",
        "bilibili",
    )
    if any(pattern.lower() in cleaned.lower() for pattern in noise_patterns):
        return None

    if not re.search(r"[\u4e00-\u9fff]", cleaned):
        return None

    return cleaned


def merge_ocr_reads(
    *,
    season: int,
    episode: int,
    source: str,
    reads: list[OcrRead],
    sample_interval_ms: int = 1000,
) -> list[LineRecord]:
    cleaned_reads = [
        OcrRead(time_ms=read.time_ms, text=cleaned, screenshot_key=read.screenshot_key)
        for read in sorted(reads, key=lambda item: item.time_ms)
        if (cleaned := clean_ocr_text(read.text)) is not None
    ]
    if not cleaned_reads:
        return []

    records: list[LineRecord] = []
    current = cleaned_reads[0]
    current_end = current.time_ms + sample_interval_ms

    for read in cleaned_reads[1:]:
        if read.text == current.text and read.time_ms <= current_end + sample_interval_ms:
            current_end = read.time_ms + sample_interval_ms
            continue

        records.append(
            _line_record(
                season=season,
                episode=episode,
                source=source,
                start_ms=current.time_ms,
                end_ms=current_end,
                text=current.text,
                screenshot_key=current.screenshot_key,
            )
        )
        current = read
        current_end = read.time_ms + sample_interval_ms

    records.append(
        _line_record(
            season=season,
            episode=episode,
            source=source,
            start_ms=current.time_ms,
            end_ms=current_end,
            text=current.text,
            screenshot_key=current.screenshot_key,
        )
    )
    return records


def _line_record(
    *,
    season: int,
    episode: int,
    source: str,
    start_ms: int,
    end_ms: int,
    text: str,
    screenshot_key: str,
) -> LineRecord:
    return LineRecord(
        id=f"S{season:02d}E{episode:02d}-{start_ms:09d}",
        season=season,
        episode=episode,
        source=source,
        start_ms=start_ms,
        end_ms=end_ms,
        text=text,
        screenshot_key=screenshot_key,
    )
