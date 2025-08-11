## VK Group Downloads Feature Plan

This document describes how to implement features to download the following objects from VK communities (groups): community metadata, wall content, photos, videos, documents, and stories. Users can download any subset of these types or all of them. Each type is stored in its own subfolder under the group’s download directory.

Reference: [VK API Reference](https://dev.vk.com/en/reference)

### Scope

- **Supported object types**: community metadata, wall content, photos, videos, documents, stories.
- **Selection**: user can choose one or more types, or "all".
- **Storage**: partition by group, then by type subfolder.
- **Access**: supports public groups and groups where the token has access. Requires appropriate VK scopes per type.

### Storage layout

Base directory below `downloads/` using `<group-id>-<group-title>` naming.

```
downloads/
  <group-id>-<group-title>/
    metadata/
      group.yaml
    wall/
      posts.yaml
      attachments/
        photos/...           # normalized when extracted
        videos/...
        docs/...
    photos/
      <album-id>-<album-title>/
        info.yaml                 # album metadata
        -<group-id>-<photo-id>.<extension>
    videos/
      videos.yaml
      files/<video_id>.mp4   # when downloadable; else save player URLs
    documents/
      docs.yaml
      files/<doc_id>_<name>
    stories/
      stories.yaml
      files/<story_id>.(mp4|jpg)
```

Notes:
- Prefer YAML for stored metadata. For very large collections, use YAML arrays or split into chunked files (e.g., `posts_part1.yaml`, `posts_part2.yaml`).
- Preserve raw API payloads along with minimal normalized indexes where helpful (e.g., per-album `info.yaml`, optional top-level indexes).
- Include a `meta.yaml` at the root with run parameters, token scopes, API version, and timestamps.

### Token scopes and permissions

- **groups**: read group info and member-related fields.
- **wall**: read wall posts.
- **photos**: read photos and albums.
- **video**: read videos.
- **docs**: read documents.
- **stories**: read stories.
- Some content may be restricted by privacy settings or require admin rights (e.g., certain statistics, private posts). Use `owner_id = -<group_id>` for community-owned content.

### CLI and configuration UX

- Command (example):
  - `uv run vk-archiver download --group <screen_name|id> --types metadata,wall,photos,videos,documents,stories --output downloads --since 2024-01-01 --until 2025-01-01 --max-items 10000 --concurrency 8`
- Flags/options:
  - `--group`: group screen name or numeric id (without minus). Resolve to `group_id` internally.
  - `--types`: comma-separated list or `all`.
  - `--output`: base directory (default `downloads`).
  - `--since` / `--until`: filter by date where applicable (wall, stories), UTC. If omitted, no time filter is applied (download full history).
  - `--max-items`: per type cap. If omitted, no cap (download all items until exhausted).
  - `--concurrency`: number of parallel API fetches/downloads.
  - `--resume`: resume from saved cursors/offsets if present.
  - `--api-version`: VK API version override.
  - `--dry-run`: print plan only.

- Defaults behavior:
  - If `--since`, `--until`, and `--max-items` are not provided, the downloader attempts to fetch the complete history for each selected type.
  - Existing files are not re-downloaded; the downloader skips files that already exist on disk.

### High-level architecture

- Resolver
  - Resolve `--group` to `group_id`, `screen_name`, and canonical folder name.
- Token and scope validator
  - Introspect token scopes (or attempt minimal calls) and warn when required scopes are missing.
- Downloader orchestrator
  - Parses `--types` and invokes type-specific downloaders.
  - Maintains shared rate limiter and retry/backoff policy.
  - Persists per-type cursors (`state.json`) to support `--resume`.
- Type-specific downloaders (modular)
  - `MetadataDownloader`, `WallDownloader`, `PhotosDownloader`, `VideosDownloader`, `DocumentsDownloader`, `StoriesDownloader`.
  - Each handles pagination, filtering, normalization, and file writes for its domain.
- Storage service
  - Ensures directory structure, temp-file writes with atomic rename, and deduping.
  - Skips file downloads when the target path already exists; optionally verify size/hash when known to avoid partial duplicates.
- Logging and metrics
  - Structured logs, per-type counters, and summary at end.

### Endpoints per type (typical)

- **Community metadata**
  - `groups.getById` (fields: description, members_count, links, contacts, cover, etc.)
  - Possibly `groups.get` for extended info when authorized.
- **Wall content**
  - `wall.get` with `owner_id = -group_id`; handle pagination via `offset`/`count`.
  - Optional filtering by `date` after fetch; VK does not provide direct date filters for wall.
- **Photos**
  - `photos.getAlbums`, `photos.get` or `photos.getAll` with `owner_id = -group_id`.
  - For file downloads, pick the largest `sizes` URL available.
- **Videos**
  - `video.get` with `owner_id = -group_id` (and albums via `video.getAlbums`).
  - Depending on permissions, `files` URLs may be absent; store `player` URL when direct files are unavailable.
- **Documents**
  - `docs.get` with `owner_id = -group_id`.
- **Stories**
  - `stories.get` for owner; stories are ephemeral; availability requires scope and recent content.

See [VK API Reference](https://dev.vk.com/en/reference) for fields and versioning notes.

### Implementation steps

1) Bootstrapping
   - Add CLI options and command for `download` with `--group`, `--types`, and shared flags.
   - Implement group resolver (screen name to id) using `utils.resolve_group` (new) calling `groups.getById`.

2) Shared infrastructure
   - Build a thin VK API client: base URL, `v` param, token auth, rate limiter, and retry with exponential backoff on transient errors.
   - Implement pagination helpers returning generators/iterators yielding items.
   - Implement storage service to create folders, write JSONL, and atomic file saves.

3) MetadataDownloader
   - Fetch `groups.getById` with rich `fields` set.
   - Save raw response to `metadata/group.yaml` and update root `meta.yaml`.

4) WallDownloader
   - Iterate `wall.get` pages until done or `--max-items` reached.
   - Apply `--since/--until` filtering.
   - Write posts to `wall/posts.yaml` (single YAML array or chunked `posts_partN.yaml`).
   - Optionally extract attachments to `wall/attachments/<type>/...` (photo/video/doc links only when feasible).
   - Default (no `--since/--until`/`--max-items`): fetch all posts until API exhaustion.

5) PhotosDownloader
   - Fetch albums (`photos.getAlbums`), then photos (`photos.get`/`photos.getAll`).
   - For each album, create `photos/<album-id>-<album-title>/info.yaml` with album metadata.
   - Download best-quality `sizes.url` for each photo into the album directory as `-<group-id>-<photo-id>.<extension>`, skipping files that already exist.
   - Optionally maintain `photos/index.yaml` with a summary index if needed.
   - Default (no `--max-items`): fetch all photos in each album until API exhaustion.

6) VideosDownloader
   - Fetch videos (`video.get`) and albums when useful.
   - Write metadata to `videos/videos.yaml`.
   - If downloadable URLs are provided, save to `videos/files/`, skipping files that already exist; else persist `player` URL only.
   - Default (no `--max-items`): fetch all videos until API exhaustion.

7) DocumentsDownloader
   - Fetch documents (`docs.get`).
   - Write metadata to `documents/docs.yaml`.
   - Download files to `documents/files/` with sanitized names, skipping files that already exist.
   - Default (no `--max-items`): fetch all documents until API exhaustion.

8) StoriesDownloader
   - Fetch stories (`stories.get`) for the owner.
   - Write metadata to `stories/stories.yaml`.
   - Download media when URLs are available; note ephemeral nature and scope requirements.
   - Default: fetch all currently available stories (stories are ephemeral; time filters may not apply).

9) Resume and idempotency
   - Maintain `state.json` per type with last fetched offsets/ids.
   - Use deduplication by `id` and owner; skip already-downloaded files based on name or checksum.
   - By default, without explicit limits, continue until the API indicates no more data; resuming should not duplicate items or files.

10) Concurrency and rate limiting
    - Batch API requests where supported; cap concurrent downloads to respect API limits.
    - Backoff on `Too many requests` and retry on 5xx.

11) Errors and observability
    - Log and continue on per-item failures; summarize failures at end.
    - Provide `--dry-run` to preview counts and plan.

12) Validation
    - After run, emit a summary report: counts per type, bytes downloaded, time taken, skipped/failed.

### Edge cases and constraints

- Private or restricted groups: some types may be unavailable even with token.
- Deleted/blocked content: handle 403/404 gracefully.
- Ephemeral stories: may vanish before download completes.
- Video direct links may be absent; store references instead of files.
- Wall pagination can be large; implement partial runs via `--max-items` and `--resume`.
- File name sanitization and length limits on certain filesystems.

### Testing checklist

- Unit tests for: resolver, pagination, retry, storage writes, file naming, YAML writers/readers, and per-type normalizers.
- Integration tests against VK API mock/fakes for each type downloader.
- E2E smoke test against a public demo group with `--types=metadata` and `--types=photos` limited by `--max-items`.

### Future enhancements

- Incremental sync by `post_id`/`date` cursors per type.
- Optional extraction of comments/likes for wall posts.
- Parallel group downloads.
- HTML report summarizing downloaded content with thumbnails.


