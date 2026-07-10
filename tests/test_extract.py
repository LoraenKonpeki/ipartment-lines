from ipartment_lines.extract import (
    build_exact_seek_command,
    build_extract_command,
    iter_sample_times,
    pick_recognition_region,
)


def test_iter_sample_times_includes_start_and_stops_before_end():
    assert list(iter_sample_times(1000, 5000, 2000)) == [1000, 3000]


def test_pick_recognition_region_uses_center_band():
    assert pick_recognition_region({"x": 360, "y": 790, "w": 1200, "h": 230}) == {
        "x": 80,
        "y": 35,
        "w": 1040,
        "h": 170,
    }


def test_pick_recognition_region_uses_lower_wide_band_for_middle_seasons():
    assert pick_recognition_region({"x": 360, "y": 790, "w": 1200, "h": 230}, season=2) == {
        "x": 39,
        "y": 79,
        "w": 1119,
        "h": 144,
    }


def test_build_extract_command_samples_by_frame_number_not_pts_fps():
    command = build_extract_command(
        video_path="source.mp4",
        crop={"x": 360, "y": 790, "w": 1200, "h": 230},
        start_ms=7_200_000,
        end_ms=7_260_000,
        sample_interval_ms=5_000,
        sample_frame_rate=24.0,
        ffmpeg_threads=2,
    )

    vf = command[command.index("-vf") + 1]
    assert "select=not(mod(n\\,120))" in vf
    assert "fps=" not in vf


def test_build_exact_seek_command_extracts_one_crop_at_absolute_time():
    command = build_exact_seek_command(
        video_path="source.mp4",
        crop={"x": 360, "y": 790, "w": 1200, "h": 230},
        time_ms=7_250_000,
        ffmpeg_threads=1,
    )

    assert command[:4] == ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    assert command[command.index("-ss") + 1] == "7250.000"
    assert command[command.index("-frames:v") + 1] == "1"
    assert command[command.index("-vf") + 1] == "crop=1200:230:360:790"
