from pathlib import Path

from ipartment_lines.frames import build_ffmpeg_crop_command, render_crop_gallery, select_crop_samples


def test_build_ffmpeg_crop_command_uses_manifest_crop_values():
    command = build_ffmpeg_crop_command(
        video_path="/videos/S01.mp4",
        time_ms=8_400_000,
        crop={"x": 360, "y": 790, "w": 1200, "h": 230},
        output_path=Path("/tmp/S01E01.jpg"),
    )

    assert command == [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        "8400.000",
        "-i",
        "/videos/S01.mp4",
        "-frames:v",
        "1",
        "-vf",
        "crop=1200:230:360:790",
        "-q:v",
        "2",
        "/tmp/S01E01.jpg",
    ]


def test_select_crop_samples_uses_segment_offsets_and_safe_names():
    manifest = {
        "sources": [
            {
                "filename": "01 - 风景第一季1-5.mp4",
                "video_path": "/root/videos/01 - 风景第一季1-5.mp4",
                "crop": {"x": 360, "y": 790, "w": 1200, "h": 230},
                "segments": [
                    {"id": "S01E01", "start_ms": 7_200_000, "end_ms": 10_000_000},
                    {"id": "S01E02", "start_ms": 10_000_000, "end_ms": 12_800_000},
                ],
            }
        ]
    }

    samples = select_crop_samples(manifest, offset_ms=60_000)

    assert len(samples) == 2
    assert samples[0].segment_id == "S01E01"
    assert samples[0].time_ms == 7_260_000
    assert samples[0].filename == "S01E01_007260000.jpg"
    assert samples[1].filename == "S01E02_010060000.jpg"


def test_select_crop_samples_can_use_start_middle_end_points():
    manifest = {
        "sources": [
            {
                "filename": "01 - 风景第一季1-5.mp4",
                "video_path": "/root/videos/01 - 风景第一季1-5.mp4",
                "crop": {"x": 360, "y": 790, "w": 1200, "h": 230},
                "segments": [
                    {"id": "S01E01", "start_ms": 7_200_000, "end_ms": 10_000_000},
                ],
            }
        ]
    }

    samples = select_crop_samples(manifest, points=["start+60s", "mid", "end-60s"])

    assert [sample.label for sample in samples] == ["start+60s", "mid", "end-60s"]
    assert [sample.time_ms for sample in samples] == [7_260_000, 8_600_000, 9_940_000]
    assert [sample.filename for sample in samples] == [
        "S01E01_start_60s_007260000.jpg",
        "S01E01_mid_008600000.jpg",
        "S01E01_end_60s_009940000.jpg",
    ]


def test_render_crop_gallery_groups_samples_by_segment():
    manifest = {
        "sources": [
            {
                "filename": "01 - 风景第一季1-5.mp4",
                "segments": [
                    {"id": "S01E01", "start_ms": 7_200_000, "end_ms": 10_000_000},
                ],
            }
        ]
    }
    samples = select_crop_samples(
        {
            "sources": [
                {
                    "filename": "01 - 风景第一季1-5.mp4",
                    "video_path": "/root/videos/01 - 风景第一季1-5.mp4",
                    "crop": {"x": 360, "y": 790, "w": 1200, "h": 230},
                    "segments": [
                        {"id": "S01E01", "start_ms": 7_200_000, "end_ms": 10_000_000},
                    ],
                }
            ]
        },
        points=["start+60s", "mid"],
    )

    html = render_crop_gallery(samples, manifest=manifest)

    assert "<h2>S01E01</h2>" in html
    assert "01 - 风景第一季1-5.mp4" in html
    assert "S01E01_start_60s_007260000.jpg" in html
    assert "02:01:00" in html
