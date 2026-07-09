# ipartment-lines

Local tooling for building a searchable subtitle and screenshot index from user-provided video files.

This repository intentionally does not include videos, screenshots, or extracted full subtitle datasets.

## MVP

- Read a Bilibili-style `parts.tsv` and local/remote video directory layout.
- Generate an editable manifest for collection videos that contain several episodes.
- Extract frames from a configurable subtitle crop area.
- OCR hard subtitles into timestamped line records.
- Build a compressed browser-searchable JSON database.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Generate A Manifest From The Current mini Source

Run this on a machine that can read the metadata files. The generated files live under ignored `data/` paths.

```bash
mkdir -p data/raw/mini-BV1xQ9ZBGEJ2 data/generated
scp mini:/root/videos/bilibili/BV1xQ9ZBGEJ2/parts.tsv data/raw/mini-BV1xQ9ZBGEJ2/parts.tsv
scp mini:/root/videos/bilibili/BV1xQ9ZBGEJ2/metadata.json data/raw/mini-BV1xQ9ZBGEJ2/metadata.json

PYTHONPATH=src python3 -m ipartment_lines.cli build-manifest \
  --parts data/raw/mini-BV1xQ9ZBGEJ2/parts.tsv \
  --metadata data/raw/mini-BV1xQ9ZBGEJ2/metadata.json \
  --video-root /root/videos/bilibili/BV1xQ9ZBGEJ2 \
  --output data/generated/manifest.json
```

The manifest uses an editable default subtitle crop:

```json
{"x": 360, "y": 790, "w": 1200, "h": 230}
```

The current source videos contain multiple episodes per file plus padding/intermission material, so generated episode boundaries are guesses. Calibrate `content_start_ms`, `content_end_ms`, and each segment before full OCR.

## Build Browser Search Data

After OCR produces normalized `LineRecord` objects as JSON:

```bash
PYTHONPATH=src python3 -m ipartment_lines.cli build-db \
  --lines data/generated/lines.json \
  --output data/generated/lines_db.gz
```

## Source Material

Put local media under `data/raw/`, or point the manifest at an existing absolute path such as:

```text
/root/videos/bilibili/BV1xQ9ZBGEJ2
```

The `data/`, `frames/`, and `screenshots/` directories are ignored by git.
