from pathlib import Path

from ipartment_lines.screenshots import (
    ScreenshotJob,
    prepare_fresh_output_dir,
    build_ffmpeg_command,
    build_screenshot_jobs,
    pending_jobs,
)


def test_build_screenshot_jobs_uses_source_and_screenshot_key(tmp_path):
    records = [
        {
            "source": "01 - 风景第一季1-5.mp4",
            "start_ms": 7210000,
            "screenshot_key": "S01E01/007210000.webp",
        }
    ]

    jobs = build_screenshot_jobs(
        records,
        video_root=tmp_path / "videos",
        output_root=tmp_path / "shots",
    )

    assert jobs == [
        ScreenshotJob(
            video_path=tmp_path / "videos" / "01 - 风景第一季1-5.mp4",
            time_ms=7210000,
            output_path=tmp_path / "shots" / "S01E01" / "007210000.webp",
        )
    ]


def test_pending_jobs_skips_existing_nonempty_outputs(tmp_path):
    existing = tmp_path / "existing.webp"
    existing.write_bytes(b"webp")
    missing = tmp_path / "missing.webp"
    jobs = [
        ScreenshotJob(Path("video.mp4"), 1000, existing),
        ScreenshotJob(Path("video.mp4"), 2000, missing),
    ]

    assert list(pending_jobs(jobs)) == [jobs[1]]


def test_prepare_fresh_output_dir_archives_existing_screenshots(tmp_path):
    output_dir = tmp_path / "screenshots_1280"
    existing = output_dir / "S01E01" / "007210000.webp"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"old-image")

    archive = prepare_fresh_output_dir(output_dir, archive_tag="before-exact-123")

    assert archive == tmp_path / "screenshots_1280.before-exact-123"
    assert (archive / "S01E01" / "007210000.webp").read_bytes() == b"old-image"
    assert output_dir.is_dir()
    assert not any(output_dir.iterdir())


def test_build_ffmpeg_command_scales_to_width_and_webp_quality(tmp_path):
    job = ScreenshotJob(
        video_path=tmp_path / "source.mp4",
        time_ms=1500,
        output_path=tmp_path / "shot.webp",
    )

    command = build_ffmpeg_command(job, width=1280, quality=80)

    assert command[:4] == ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    assert "-ss" in command
    assert "1.500" in command
    assert str(job.video_path) in command
    assert "scale=1280:-2" in command
    assert "-quality" in command
    assert "80" in command
    assert str(job.output_path) in command
