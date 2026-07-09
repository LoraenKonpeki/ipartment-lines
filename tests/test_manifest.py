from ipartment_lines.manifest import build_episode_segments
from ipartment_lines.manifest import build_manifest
from ipartment_lines.sources import SourcePart


def test_build_episode_segments_divides_program_window_evenly():
    part = SourcePart(
        page=1,
        filename="01 - 风景第一季1-5.mp4",
        title="风景第一季1-5",
        season=1,
        first_episode=1,
        last_episode=5,
        duration_ms=21_210_000,
    )

    segments = build_episode_segments(part, content_start_ms=7_200_000, content_end_ms=21_210_000)

    assert [segment.episode for segment in segments] == [1, 2, 3, 4, 5]
    assert segments[0].start_ms == 7_200_000
    assert segments[-1].end_ms == 21_210_000
    assert segments[0].segment_id == "S01E01"


def test_build_manifest_uses_metadata_durations_and_default_crop():
    parts_tsv = "\n".join(
        [
            "page\tcid\tpart\tfilename",
            "1\t1\t风景第一季1-5\t01 - 风景第一季1-5.%(ext)s",
            "19\t2\t点点关注不迷路，补档一辈子\t19 - 点点关注不迷路，补档一辈子.%(ext)s",
        ]
    )
    metadata = {"pages": [{"page": 1, "duration": 21210}]}

    manifest = build_manifest(
        parts_tsv=parts_tsv,
        metadata=metadata,
        video_root="/root/videos/bilibili/BV1xQ9ZBGEJ2",
    )

    assert len(manifest["sources"]) == 1
    source = manifest["sources"][0]
    assert source["filename"] == "01 - 风景第一季1-5.mp4"
    assert source["duration_ms"] == 21_210_000
    assert source["content_start_ms"] == 7_200_000
    assert source["crop"] == {"x": 360, "y": 790, "w": 1200, "h": 230}
    assert source["segments"][0]["id"] == "S01E01"
