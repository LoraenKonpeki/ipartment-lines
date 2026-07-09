from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SourcePart:
    page: int
    filename: str
    title: str
    season: int
    first_episode: int
    last_episode: int
    duration_ms: int | None = None


CHINESE_NUMBERS = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
}


def parse_part_title(title: str) -> SourcePart | None:
    match = re.search(r"第([一二三四五])季(\d+)-(\d+)", title)
    if not match:
        return None

    season_text, first_episode, last_episode = match.groups()
    return SourcePart(
        page=0,
        filename="",
        title=title,
        season=CHINESE_NUMBERS[season_text],
        first_episode=int(first_episode),
        last_episode=int(last_episode),
    )


def parse_parts_tsv(text: str) -> list[SourcePart]:
    parts: list[SourcePart] = []
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return parts

    header = lines[0].split("\t")
    columns = {name: index for index, name in enumerate(header)}

    for row in lines[1:]:
        values = row.split("\t")
        title = values[columns["part"]]
        parsed = parse_part_title(title)
        if parsed is None:
            continue

        filename_template = values[columns["filename"]]
        filename = filename_template.replace("%(ext)s", "mp4")
        parts.append(
            SourcePart(
                page=int(values[columns["page"]]),
                filename=filename,
                title=title,
                season=parsed.season,
                first_episode=parsed.first_episode,
                last_episode=parsed.last_episode,
            )
        )

    return parts
