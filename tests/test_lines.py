from ipartment_lines.lines import OcrRead, clean_ocr_text, merge_ocr_reads


def test_clean_ocr_text_removes_noise_and_normalizes_spaces():
    assert clean_ocr_text("  不行  我这是婚车，接新娘子的  ") == "不行 我这是婚车，接新娘子的"
    assert clean_ocr_text("关注不迷路\n补档一辈子") is None
    assert clean_ocr_text("IP江西") is None


def test_merge_ocr_reads_merges_adjacent_duplicate_text():
    reads = [
        OcrRead(time_ms=1000, text="不行 我这是婚车", screenshot_key="S01E01/1000.webp"),
        OcrRead(time_ms=2000, text="不行 我这是婚车", screenshot_key="S01E01/2000.webp"),
        OcrRead(time_ms=5000, text="接新娘子的", screenshot_key="S01E01/5000.webp"),
    ]

    lines = merge_ocr_reads(season=1, episode=1, source="01 - 风景第一季1-5.mp4", reads=reads)

    assert len(lines) == 2
    assert lines[0].id == "S01E01-000001000"
    assert lines[0].start_ms == 1000
    assert lines[0].end_ms == 3000
    assert lines[0].text == "不行 我这是婚车"
