# ipartment-lines MVP Design

## Goal

Build a local-first toolchain that turns user-provided hard-subtitled videos into a searchable line database with screenshot references. The project stores code and configuration only; source videos, generated screenshots, OCR output, and full subtitle databases stay outside git.

## Current Source Layout

The available source on `mini` is `/root/videos/bilibili/BV1xQ9ZBGEJ2`. It contains 18 collection videos for seasons 1-4 plus one non-content part. Each collection video contains 4-5 episodes and may include long intro/intermission material before the actual episode content. The video stream is 1920x1080 AV1 at 24fps. Sample frames show bottom-centered hard subtitles across seasons, roughly in the lower 20% of the frame.

## MVP Architecture

The first version is a Python package with small CLI-friendly modules:

- `ipartment_lines.sources`: parse source part names such as `风景第一季1-5` into season and episode ranges.
- `ipartment_lines.manifest`: generate an editable manifest with one source part and candidate episode segments.
- `ipartment_lines.lines`: normalize OCR output, filter uploader noise, merge duplicate adjacent reads, and emit line records.
- `ipartment_lines.search_db`: compress normalized line records into a browser-loadable JSON gzip file.

The web layer can stay static for the first pass. It will load the generated compressed JSON and run local text search in the browser, similar to VV but without face similarity fields.

## Data Model

Each searchable line record contains:

```json
{
  "id": "S01E01-0008400",
  "season": 1,
  "episode": 1,
  "source": "01 - 风景第一季1-5.mp4",
  "start_ms": 8400000,
  "end_ms": 8402500,
  "text": "不行 我这是婚车 接新娘子的",
  "screenshot_key": "S01E01/8400000.webp"
}
```

Episode boundaries are initially generated as editable guesses because the source videos are collections with non-program padding. A later calibration pass can refine `start_ms` and `end_ms` per episode.

## OCR Strategy

Default subtitle crop for 1920x1080 sources is a bottom band, approximately `x=360, y=790, w=1200, h=230`. This deliberately excludes top-left uploader text, the top-right Bilibili watermark, and the episode number. The crop is configurable per source part because some seasons or uploads may shift subtitle placement.

OCR should sample at a configurable interval, starting with 1 frame per second. Adjacent identical OCR results are merged into one line interval. Noise filters remove known uploader/intermission text such as `关注不迷路`, `补档`, `IP江西`, `跳转至`, and empty/non-Chinese fragments.

## Verification

Core parsing and normalization logic is test-driven. Media/OCR integration is verified with a short sample clip or a small set of extracted frames from `mini`. Full-series OCR is not part of this first commit because it is long-running and depends on OCR runtime setup on `mini`.

