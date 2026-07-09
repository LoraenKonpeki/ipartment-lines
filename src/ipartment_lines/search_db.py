from __future__ import annotations

import gzip
import json

from .lines import LineRecord


def encode_search_database(records: list[LineRecord]) -> bytes:
    compact = [
        {
            "id": record.id,
            "se": record.season,
            "ep": record.episode,
            "src": record.source,
            "st": record.start_ms,
            "en": record.end_ms,
            "x": record.text,
            "img": record.screenshot_key,
        }
        for record in records
    ]
    payload = json.dumps(compact, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return gzip.compress(payload, compresslevel=9)
