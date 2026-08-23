# Publishing medias from a backend

Getting files into the platform, encoded and published, without a human in the back office.

## Upload

Small to medium files, in one request — `POST /medias`, multipart, JSON in a part named `resource`:

```bash
curl -X POST "https://api.streamlike.com/medias" \
  -H 'X-Streamlike-Authorization: streamlikeAuth token="YOUR_KEY"' \
  -F 'resource={"name":"Board meeting","permalink":"board-meeting-2026-08","type":"video","visibility":{"state":"offline"}};type=application/json' \
  -F "source[media_file]=@meeting.mp4;type=video/mp4" \
  -F "cover=@cover.jpg;type=image/jpeg"
```

`201` returns the media, including its `media_id`. Publish later by switching
`visibility.state` to `online` — uploading straight to `online` publishes a media whose encoding is
not finished.

Large or unreliable sources: drop the file on the account's FTP watchfolder, then pull it in with
`POST /medias/{media_ids}/actions/retrieve`, or let the watchfolder create the media on its own.
Steadier than a long HTTP upload, and resumable by nature.

Check field names before writing the payload:

```bash
scripts/openapi_lookup.py show /medias --method post
```

## Follow the encoding

Encoding is asynchronous. A freshly created media is not playable, and its manifest does not exist
yet.

- `GET /pipelines` lists the pipelines and their jobs, with their state and their error when one failed (the job *log* itself is staff-only and answers `403`),
- `GET /medias?encoded=1` — and `encoded=1` on `/ws/playlist` — filter on medias whose encoding
  finished. Poll that rather than guessing a delay,
- `POST /jobs/{job_id}/restart` re-runs a failed job, `POST /medias/{media_ids}/actions/reencode`
  re-encodes from the source — but not a multi-track media, which answers
  `INVALID_MEDIA_IS_MULTIPLE_AUDIO`: its tracks are managed one by one.

Front ends should never show a media that is still encoding: filter on `encoded`, or keep the media
`offline` until you have seen it finish.

## Enrich

| Goal | Call |
| --- | --- |
| Subtitles | `POST /medias/{media_id}/subtitles/{language_id}` |
| Automatic subtitles | `POST /medias/{media_ids}/actions/speechtotext` |
| Chapters | `POST /medias/{media_id}/chapters/{language_id}` |
| Interactions (clickable overlays) | `POST /medias/{media_id}/interactions/{language_id}` |
| Audio tracks | `POST /medias/{media_id}/audio-tracks/{language_id}`, `…/promote` for a single-track media |
| Replace the video, keeping the tracks | `POST /medias/{media_id}/video/replace` |
| Cover from a frame | `POST /medias/{media_id}/cover/screenshot` |
| Tags, keywords, playlists | `POST /medias/{media_ids}/actions/organization/{tag\|keyword\|playlist}` |
| Custom fields | Templates under `/medias/customfields`, values in the media payload |

Remember the collection rule: sending `keyword_ids` replaces the whole list, so read, merge, then
write. `{"keyword_ids": []}` empties it.

## Publish

```bash
curl -X PATCH "https://api.streamlike.com/medias/MEDIA_ID" \
  -H 'X-Streamlike-Authorization: streamlikeAuth token="YOUR_KEY"' \
  -H "Content-Type: application/json" \
  -d '{"visibility":{"state":"online"}}'
```

States are `online`, `offline` and `archived`. Bulk changes go through
`POST /medias/{media_ids}/actions/visibility/state`, with ids separated by commas — the whole
`Medias - Actions` family works that way and is much cheaper than a loop of single calls.

## Housekeeping

- **retries**: a `5xx` deserves a retry with backoff; a `400` never does — read
  `data.errors` and fix the payload,
- **conflicts**: `409` means an operation is already running on that media (a re-encode, an audio
  track update). Wait and retry — `source.encoding_operation_running` on `GET /medias/{media_id}`
  tells you when it is over, which beats retrying on a timer,
- **idempotency**: `permalink` is a good deduplication key for a pipeline that may run twice — but
  it is unique platform-wide, not per account, and deleted medias still hold theirs. A generic
  slug can come back as `INVALID_PERMALINK` even though nothing in your catalog uses it; prefix
  yours,
- **soft deletion**: deleting a media hides it from the API and the webservices, but a front end
  holding a cached id will get a `404`. Refresh caches after a purge,
- **archives**: `Hibernation` endpoints hold medias moved out of active storage. They are not
  playable until retrieved.
