import gzip
import json

from ipartment_lines.lines import LineRecord
from ipartment_lines.search_db import encode_search_database


def test_encode_search_database_uses_compact_keys():
    records = [
        LineRecord(
            id="S01E01-000001000",
            season=1,
            episode=1,
            source="01 - 风景第一季1-5.mp4",
            start_ms=1000,
            end_ms=3000,
            text="不行 我这是婚车",
            screenshot_key="S01E01/1000.webp",
        )
    ]

    compressed = encode_search_database(records)
    decoded = json.loads(gzip.decompress(compressed).decode("utf-8"))

    assert decoded == [
        {
            "id": "S01E01-000001000",
            "se": 1,
            "ep": 1,
            "src": "01 - 风景第一季1-5.mp4",
            "st": 1000,
            "en": 3000,
            "x": "不行 我这是婚车",
            "img": "S01E01/1000.webp",
        }
    ]
