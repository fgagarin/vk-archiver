# VK Archiver CLI

<div align="center">
  <a href="https://github.com/fgagarin/vk-archiver">
    <img src="https://img.shields.io/github/stars/fgagarin/vk-archiver" alt="Stars Badge"/>
  </a>
</div>

Command-line tool to download VK community content: metadata, wall posts, photos, videos, documents, and stories. Saves structured YAML metadata alongside files. Token-only authentication; no login/password.

## Requirements

- Python 3.10+
- Internet access
- VK access token (see below)

## Install and run with uv

Recommended via `uv` for isolated env and dependency management:

```bash
# Install uv (see https://github.com/astral-sh/uv)

# Run the CLI directly (no manual env activation needed)
uv run vk-archiver --help

# Or create a local environment and install dependencies (including dev)
uv sync
```

Alternative (pip):
```bash
pip install -r requirements.txt
```

## Get a VK access token

Use an official method to obtain a token with the required scopes:

- Recommended: `https://vkhost.github.io/` — request scopes as needed: `groups, wall, photos, video, docs, stories`.

Provide the token either via environment or config:

- Environment:
```bash
export VK_TOKEN=YOUR_TOKEN_HERE
```
- Or in `vk_archiver/config.yaml`:
```yaml
token: YOUR_TOKEN_HERE
```

> Note: login/password auth is not supported and is explicitly forbidden.

## CLI usage

General form:
```bash
uv run vk-archiver [OPTIONS] COMMAND [ARGS]...
```

Global options:
- `-o, --output-dir` — base output directory (default `./downloads`)
- `-r, --rate-limit` — VK API requests per second (default 3)

### Universal community download
```bash
uv run vk-archiver download \
  --group <screen_name|id> \
  --types metadata,wall,photos,videos,documents,stories \
  --output downloads \
  --since 2024-01-01 \
  --until 2025-01-01 \
  --max-items 500 \
  --concurrency 8 \
  --resume \
  --dry-run
```

Examples:
```bash
# Metadata only
uv run vk-archiver download --group habr --types metadata

# Wall with date filters
uv run vk-archiver download --group 1 --types wall --since 2024-01-01 --max-items 200

# Albums with parallel downloads
uv run vk-archiver download --group mygroup --types photos --concurrency 8

# Videos (yt-dlp). Errors are written to *_error.txt
uv run vk-archiver download --group mygroup --types videos --max-items 50

# Documents and stories
uv run vk-archiver download --group mygroup --types documents,stories
```

## Storage layout

```
downloads/
  <group-id>-<group-title>/
    metadata/group.yaml
    wall/posts.yaml
    wall/attachments/photos/links.yaml
    wall/attachments/photos/<owner_id>_<photo_id>.jpg
    photos/<album-id>-<album-title>/info.yaml
    photos/<album-id>-<album-title>/<group-id>-<photo-id>.<ext>
    videos/videos.yaml
    videos/files/<video_id>.mp4
    documents/docs.yaml
    documents/files/<doc_id>_<name>.<ext>
    stories/stories.yaml
    stories/files/<story_id>.(mp4|jpg)
    state.json
```

## Resume and error handling

- Resume: `state.json` in the group root keeps cursors/offsets.
- Idempotency: existing files are skipped.
- Errors: per-file `*_error.txt` markers are created with details; files are retried on the next run.

## Credits

This project is a fork of the original `vk-archiver` by YarikMix. Many ideas and parts of the implementation were inspired by and/or adapted from the upstream project.

- Original repository: `https://github.com/YarikMix/vk-archiver`