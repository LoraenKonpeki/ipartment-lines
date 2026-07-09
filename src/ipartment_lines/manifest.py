from __future__ import annotations

from dataclasses import dataclass

from .sources import SourcePart, parse_parts_tsv


DEFAULT_SUBTITLE_CROP = {"x": 360, "y": 790, "w": 1200, "h": 230}
DEFAULT_CONTENT_START_MS = 7_200_000


@dataclass(frozen=True)
class EpisodeSegment:
    segment_id: str
    season: int
    episode: int
    source_filename: str
    start_ms: int
    end_ms: int


def build_episode_segments(
    part: SourcePart,
    *,
    content_start_ms: int = 0,
    content_end_ms: int | None = None,
) -> list[EpisodeSegment]:
    end_ms = content_end_ms if content_end_ms is not None else part.duration_ms
    if end_ms is None:
        raise ValueError("content_end_ms or part.duration_ms is required")
    if content_start_ms >= end_ms:
        raise ValueError("content_start_ms must be smaller than content_end_ms")

    episode_count = part.last_episode - part.first_episode + 1
    if episode_count <= 0:
        raise ValueError("episode range must contain at least one episode")

    duration = end_ms - content_start_ms
    segments: list[EpisodeSegment] = []
    for index, episode in enumerate(range(part.first_episode, part.last_episode + 1)):
        start = content_start_ms + (duration * index // episode_count)
        segment_end = content_start_ms + (duration * (index + 1) // episode_count)
        segment_id = f"S{part.season:02d}E{episode:02d}"
        segments.append(
            EpisodeSegment(
                segment_id=segment_id,
                season=part.season,
                episode=episode,
                source_filename=part.filename,
                start_ms=start,
                end_ms=segment_end,
            )
        )

    return segments


def build_manifest(
    *,
    parts_tsv: str,
    metadata: dict,
    video_root: str,
    default_content_start_ms: int = DEFAULT_CONTENT_START_MS,
    default_crop: dict[str, int] | None = None,
) -> dict:
    crop = default_crop or DEFAULT_SUBTITLE_CROP
    durations = {
        int(page["page"]): int(float(page["duration"]) * 1000)
        for page in metadata.get("pages", [])
        if "page" in page and "duration" in page
    }

    sources = []
    for part in parse_parts_tsv(parts_tsv):
        duration_ms = durations.get(part.page)
        if duration_ms is None:
            continue

        part_with_duration = SourcePart(
            page=part.page,
            filename=part.filename,
            title=part.title,
            season=part.season,
            first_episode=part.first_episode,
            last_episode=part.last_episode,
            duration_ms=duration_ms,
        )
        content_start_ms = min(default_content_start_ms, max(0, duration_ms - 1))
        segments = build_episode_segments(
            part_with_duration,
            content_start_ms=content_start_ms,
            content_end_ms=duration_ms,
        )
        sources.append(
            {
                "page": part.page,
                "title": part.title,
                "filename": part.filename,
                "video_path": f"{video_root.rstrip('/')}/{part.filename}",
                "season": part.season,
                "first_episode": part.first_episode,
                "last_episode": part.last_episode,
                "duration_ms": duration_ms,
                "content_start_ms": content_start_ms,
                "content_end_ms": duration_ms,
                "crop": dict(crop),
                "segments": [
                    {
                        "id": segment.segment_id,
                        "season": segment.season,
                        "episode": segment.episode,
                        "start_ms": segment.start_ms,
                        "end_ms": segment.end_ms,
                    }
                    for segment in segments
                ],
            }
        )

    return {
        "version": 1,
        "video_root": video_root,
        "defaults": {
            "crop": dict(crop),
            "content_start_ms": default_content_start_ms,
            "sample_interval_ms": 1000,
        },
        "sources": sources,
    }
