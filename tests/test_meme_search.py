import random

from ipartment_lines.meme_search import LineImageSearch


def test_search_returns_matching_existing_image(tmp_path):
    lines = [
        {
            "id": "a",
            "season": 1,
            "episode": 1,
            "text": "好男人就是我",
            "screenshot_key": "S01E01/a.webp",
        },
        {
            "id": "b",
            "season": 2,
            "episode": 1,
            "text": "欢迎来到爱情公寓",
            "screenshot_key": "S02E01/b.webp",
        },
    ]
    image = tmp_path / "shots" / "S02E01" / "b.webp"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"webp")
    data = tmp_path / "lines.json"
    data.write_text(__import__("json").dumps(lines, ensure_ascii=False), encoding="utf-8")

    result = LineImageSearch(data, tmp_path / "shots").search("爱情")

    assert result is not None
    assert result.line_id == "b"
    assert result.image_path == image


def test_search_can_filter_by_season(tmp_path):
    lines = [
        {
            "id": "s1",
            "season": 1,
            "episode": 1,
            "text": "曾小贤",
            "screenshot_key": "S01E01/a.webp",
        },
        {
            "id": "s2",
            "season": 2,
            "episode": 1,
            "text": "曾小贤",
            "screenshot_key": "S02E01/b.webp",
        },
    ]
    for key in ("S01E01/a.webp", "S02E01/b.webp"):
        image = tmp_path / "shots" / key
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"webp")
    data = tmp_path / "lines.json"
    data.write_text(__import__("json").dumps(lines, ensure_ascii=False), encoding="utf-8")

    result = LineImageSearch(data, tmp_path / "shots").search("曾小贤", season=2)

    assert result is not None
    assert result.line_id == "s2"


def test_search_avoids_immediate_repeat_when_multiple_matches_exist(tmp_path):
    lines = [
        {
            "id": "a",
            "season": 1,
            "episode": 1,
            "text": "爱情公寓",
            "screenshot_key": "S01E01/a.webp",
        },
        {
            "id": "b",
            "season": 1,
            "episode": 1,
            "text": "爱情公寓",
            "screenshot_key": "S01E01/b.webp",
        },
    ]
    for key in ("S01E01/a.webp", "S01E01/b.webp"):
        image = tmp_path / "shots" / key
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"webp")
    data = tmp_path / "lines.json"
    data.write_text(__import__("json").dumps(lines, ensure_ascii=False), encoding="utf-8")
    search = LineImageSearch(data, tmp_path / "shots", rng=random.Random(0))

    first = search.search("爱情")
    second = search.search("爱情")

    assert first is not None
    assert second is not None
    assert second.line_id != first.line_id
