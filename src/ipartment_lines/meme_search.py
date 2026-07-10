from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import random
from typing import Any


@dataclass(frozen=True)
class SearchResult:
    line_id: str
    season: int
    episode: int
    text: str
    image_path: Path


class LineImageSearch:
    def __init__(
        self,
        lines_path: Path,
        screenshot_root: Path,
        *,
        rng: random.Random | None = None,
    ) -> None:
        self.lines_path = Path(lines_path)
        self.screenshot_root = Path(screenshot_root)
        self.rng = rng or random.Random()
        self._mtime_ns: int | None = None
        self._records: list[dict[str, Any]] = []
        self._last_by_query: dict[tuple[int | None, str], str] = {}

    def search(self, keyword: str, *, season: int | None = None) -> SearchResult | None:
        query = keyword.strip()
        if not query:
            return None

        records = self._load_records()
        matches = []
        for record in records:
            if season is not None and int(record["season"]) != season:
                continue
            if query not in str(record["text"]):
                continue
            image_path = self.screenshot_root / record["screenshot_key"]
            if image_path.exists() and image_path.stat().st_size > 0:
                matches.append((record, image_path))

        if not matches:
            return None

        key = (season, query)
        last_id = self._last_by_query.get(key)
        choices = [match for match in matches if match[0]["id"] != last_id]
        if choices:
            matches = choices

        record, image_path = self.rng.choice(matches)
        self._last_by_query[key] = str(record["id"])
        return SearchResult(
            line_id=str(record["id"]),
            season=int(record["season"]),
            episode=int(record["episode"]),
            text=str(record["text"]),
            image_path=image_path,
        )

    def _load_records(self) -> list[dict[str, Any]]:
        stat = self.lines_path.stat()
        if self._mtime_ns != stat.st_mtime_ns:
            self._records = json.loads(self.lines_path.read_text(encoding="utf-8"))
            self._mtime_ns = stat.st_mtime_ns
            self._last_by_query.clear()
        return self._records
