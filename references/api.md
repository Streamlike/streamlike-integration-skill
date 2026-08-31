# REST API

```
https://api.streamlike.com/
```

The write path and the administration path: create and edit medias, upload files, manage
playlists, users, security, lives, streamouts, and read detailed analytics.

**Server side only.** An API key carries every right of the user who created it. HTTPS only —
plain HTTP answers `404`. Requests and responses are JSON, except file uploads (multipart).

## Authentication

Three ways in, in order of preference for an integration.

**Permanent key (recommended).** Created in the back office: avatar menu → API keys, with an
optional expiry date. The key is displayed once. It is bound to the user who created it and dies
with that account.

```http
GET /medias HTTP/1.1
Host: api.streamlike.com
Content-Type: application/json
X-Streamlike-Authorization: streamlikeAuth token="YOUR_KEY"
```

**Single-use token**, when credentials are supplied by a human rather than stored:

```bash
curl -X POST "https://api.streamlike.com/authent/token/unique" \
     -d "login=LOGIN" -d "password=PASSWORD"
```

Answers `200` with a token, or `400 INVALID_LOGIN_PASSWORD`.

**Session token**, for an application already authenticated as a user: `POST
/authent/token/session` issues one, `DELETE /authent/token/session` revokes it.

Store keys the way you store database passwords: environment or secret manager, never in a repo, a
mobile bundle or front-end JavaScript. Rotate by creating a new key and deleting the old one
through `/me/keys`.

## Conventions

| Method | Use |
| --- | --- |
| `GET` | Read and search |
| `POST` | Create — and also update when the request carries a file (multipart) |
| `PATCH` | Update |
| `DELETE` | Delete |

Updates are partial: send only what changes. **Nested collections are the exception** — to add one
keyword you send the full list of keywords, because a partial list would be ambiguous. To empty a
collection, send an empty array:

```json
{"keyword_ids": []}
```

Dates follow ISO 8601: `2026-08-19T14:30:00Z` or `2026-08-19T14:30:00+02:00`.

## Listing, paging and shaping

```bash
curl -G "https://api.streamlike.com/medias" \
     -H 'X-Streamlike-Authorization: streamlikeAuth token="YOUR_KEY"' \
     --data-urlencode "range=0-49" \
     --data-urlencode "sorts[]=created_at|desc" \
     --data-urlencode "fields[]=id" \
     --data-urlencode "fields[]=name" \
     --data-urlencode "fields[]=visibility.state"
```

- `range` uses first-last indexes, default `0-25`. `range=no` returns the count alone, which is the
  cheap way to know how much there is to walk,
- `sorts[]` takes `field|asc` or `field|desc`, repeatable. Sorting is ignored when `search` is
  supplied,
- **`fields[]` must be repeated, one per value.** A comma-joined list answers `400
  INVALID_FIELDS`. Dotted paths select nested fields (`source.duration`),
- `search` is full text over the resource.

Responses wrap the payload:

```json
{"data": [ … ], "total_count": 1240, "returned_count": 50,
 "returned_first_index": 0, "returned_last_index": 49, "degraded": false}
```

`200` means the whole set is in the response, `206` means it is a slice — page on `total_count`,
not on an empty page.

## Status codes and errors

| Code | Meaning |
| --- | --- |
| `200` | Read or update succeeded, full result |
| `201` | Created, the new resource is in the body |
| `204` | Succeeded, nothing to return (deletions) |
| `206` | Partial content, a slice of the collection |
| `400` | Invalid or missing values, details in the body |
| `401` | No or invalid token |
| `403` | Authenticated, but not allowed on this resource |
| `404` | Unknown resource or endpoint — **also returned when you may not see it** |
| `409` | Conflict, e.g. an encoding operation already running on that media |
| `5xx` | Server side, retry later |

Validation errors come back as machine-readable codes:

```json
{"message": "INVALID_FORM",
 "data": {"errors": ["INVALID_PERMALINK", "INVALID_TYPE", "MANDATORY_VISIBILITY_STATE"]}}
```

Each endpoint documents its own error codes; `scripts/openapi_lookup.py errors /medias` lists them.
Match on the code, never on the message text.

One restriction worth knowing before you build around it: **deleting a live is not open to
customer accounts.** `DELETE /lives/{media_id}` requires a platform-scope role, and the bulk
delete refuses a live too, with `MANDATORY_ROLE`. Stopping a live is yours
(`POST /lives/{media_id}/stop`); removing it afterwards goes through Streamlike support.

## Four responses that are not the shape you expect

Most of this API answers a described JSON object. These four do not, and each of them breaks an
integration that was working right up to the media that triggers it.

**`GET /medias/{media_id}/sourceinfo` comes in two shapes** — same for
`GET /hibernation/{hibernated_id}/sourceinfo`. Once the media has been through the encoder the
probe is wrapped as `{"media_path", "extra_data", "info"}`. Before that, for a source registered
but not yet encoded, the MediaInfo report is returned **bare, at the top level**, with no
`media_path` and no `extra_data`. **Test for `info` before reading anything:**

```js
const report = body.info ?? body;   // wrapped once encoded, bare before
```

Reading `response.info.general` on an unencoded media has always returned nothing. Inside the
report, MediaInfo's own vocabulary and units apply and the keys depend entirely on the source file
— do not assume a fixed set.

**`POST /medias/{media_id}/export/ftp` sends its nulls, and `GET /pipelines/{pipeline_id}` does
not.** The `201` body is a pipeline object of the same shape, but here `started_at`, `ended_at`,
`duration` and — inside each job — `previous_id`, `encoding_v2_job_id` and `update_kind` come back
**present and `null`**, where `/pipelines` leaves the key out entirely. `creator` is an empty
**array** `[]` rather than an object, because an export pipeline records no creator. Code shared
between the two endpoints that tests key presence reads those nulls as real values: **test the
value, not the key**, on anything that may see both.

**The `Content-Type` of a downloaded attachment lies.**
`GET /medias/{media_id}/attachments/{position}/file` and its hibernation twin answer with bytes,
and the type is guessed from the file name extension against a short list — everything outside it,
a `.docx`, a `.zip`, a `.csv`, is served as `video/mpeg`. Use the filename in `Content-Disposition`
to name and type what you save, and never branch on `Content-Type`. It is long-standing behaviour,
not a misconfiguration on your side. `GET /medias/{media_id}/scorm` is the honest one:
`application/zip`, named `scorm12-{media_id}.zip`, and it must not be cached — a tokenized package
expires after four hours.

**A CSV answer is `application/vnd.ms-excel`**, never `text/csv`, everywhere the `format` parameter
offers it. See `references/analytics.md`.

## Uploading files

Any request carrying a file is `POST`, even when it updates. The JSON payload goes into a
multipart part named `resource`:

```http
POST /medias HTTP/1.1
Content-Type: multipart/form-data; boundary="STREAMLIKEBOUND"
X-Streamlike-Authorization: streamlikeAuth token="YOUR_KEY"

--STREAMLIKEBOUND
Content-Disposition: form-data; name="resource"

{"permalink":"my-new-video","type":"video","visibility":{"state":"online"}}
--STREAMLIKEBOUND
Content-Type: video/mp4
Content-Disposition: form-data; name="source[media_file]"; filename="mynewvideo.mp4"

[BINARY]
--STREAMLIKEBOUND
Content-Type: image/jpg
Content-Disposition: form-data; name="cover"; filename="mynewcover.jpg"

[BINARY]
--STREAMLIKEBOUND--
```

One quirk of the form layer: a form key must not start with a digit, or it is read as an array
index. Order `source[plop]` before `source[360]` when both are present.

Large sources can also be dropped on the account's FTP watchfolder and pulled in with
`POST /medias/{media_ids}/actions/retrieve` — steadier than a long HTTP upload over a poor link.

### Telling the encoder how hard the video is

`source[complexity]` is an integer from `1` to `5`, `3` by default, and it is worth setting when
you know what you are uploading. It says how hard the picture is to compress — `1` for a slide
deck or a screencast, `5` for fast motion or fine grain — and the encoder spends bitrate
accordingly. A wrong value costs bandwidth on one side or quality on the other. Out of range, the
call answers `400 INVALID_FORM` with `INVALID_SOURCE_COMPLEXITY`.

Accepted on `POST /medias` and on `PATCH /medias/{media_id}`, and readable back as
`source.complexity`. API 5.31 to 5.49 dropped it from both — it was inert on the encoder of the
day — and 5.50 brought it back, wired to what the encoder actually does.

`POST /medias/{media_ids}/actions/complexity` sets it on medias that already exist, in bulk. Two
things about it:

- **it encodes nothing.** The value is stored and applies to the *next* encoding of that media —
  a re-encode you order, a replacement video you upload. Nothing is re-queued behind your back and
  the files being served do not change. To apply it to what is published today, order the
  re-encode yourself,
- it used to refuse medias produced by the current pipeline with `INVALID_MEDIA_ENCODING_V2`. It
  no longer does, and that error code is not returned by any endpoint any more.

One consequence worth knowing if you read bitrates. On medias encoded by the current pipeline, the
bitrate reported for a rendition is what the encode **actually spent**, not a nominal value from a
table — so a simple screencast can report a small fraction of what a comparable media reported
before. It is the same picture; the number is simply true now.

## Audio tracks and video replacement

API 5.31 and later, on medias produced by the current encoding pipeline. `GET
/medias/{media_id}/audio-tracks` says whether a media is one of them, and what it carries:

```json
{"encoding_v2": true,
 "audio": [{"language": "fr", "kind": "audio", "label": "Français", "default": true},
           {"language": "en", "kind": "audio", "label": "English", "default": false}],
 "audio_default": "fr", "manageable": true, "promotable": false}
```

`manageable` false means the media predates the pipeline: read its tracks, do not try to write
them. `promotable` true means the opposite corner — a single-track media that can join per-track
management (see below). They answer two different questions and neither substitutes for the other:
a media that declares tracks is never promotable, one that declares none is never manageable. Read
`manageable` before you draw an edit control, or the write endpoints answer `404`.

**This endpoint is one of the few here that sends nulls.** All six fields are always present, and
`audio_default` and `audio[].label` come back as `null` rather than being omitted — test them for
`null`, not for absence, and fall back to the language code when a label is missing. `audio` is an
**empty array**, never a missing key, on a mono-audio media, a silent video or one never encoded.
And `audio[].language` is not an identifier: a regular track and its audio description share it.
Use the token — `audio_default` carries one — for anything you pass back to a write endpoint.

If all you need is the `encoding_v2` answer, do not make this call: since API 5.46 every media
response carries `source.encoding_version`, listings included — see *Which pipeline encoded a
media* below.

`{language_id}` is a **track token**, not just a language code: `en` for the regular track, `en-ad`
for its audio description (API 5.33 and later). The suffix is what types the track; there is no
separate field. Subtitles follow the same convention, `fr-cc` for closed captions.

| Call | Effect |
| --- | --- |
| `POST …/audio-tracks/{language_id}` | Adds the track, or replaces it when the language already exists |
| `PATCH …/audio-tracks/{language_id}` | Renames it (`label`) or makes it the default (`default`) |
| `DELETE …/audio-tracks/{language_id}` | Removes it |
| `POST …/audio-tracks/{language_id}/promote` | Declares the language of a single-track media's audio (API 5.36) |
| `POST /medias/{media_id}/video/replace` | New video, every audio track and subtitle kept |

The content of a track is `track[file]` (multipart) or `track[url]` for the platform to fetch;
`video[file]` / `video[url]` likewise. `label` and `default` are optional.

Two of these do less work than they look like. `promote` re-extracts the audio the media already
publishes under a proper language name — the video is never re-encoded. `video/replace` swaps the
picture alone, and refuses a source whose duration diverges from the published one by more than
`max(2 s, 5 %)`.

Writes are asynchronous and exclusive: while one runs, the media answers `409
ENCODING_V2_JOB_ACTIVE` and `source.encoding_operation_running` is true on `GET
/medias/{media_id}`. Poll that field rather than retrying blind.

Reading the same thing from the catalog side:

- `GET /medias/{media_id}` returns `source.audio_tracks`, the published tracks with their
  `language`, `kind`, `label` and `default`. **Single media only** — it costs a manifest read, so
  it is not served in listings (API 5.37 and later),
- `source.is_multiple_audio` is a boolean on every video and audio media, listings included, and
  `GET /medias?source.is_multiple_audio=1` filters on it,
- mass re-encoding refuses these medias (`INVALID_MEDIA_IS_MULTIPLE_AUDIO`): their tracks are
  managed one by one through the endpoints above.

## Which pipeline encoded a media

API 5.46 and later. `source.encoding_version` is an integer saying which encoder produced the files
the media publishes: `2` for the current pipeline, `1` for the legacy encoder. It is served
everywhere a media is — single media, listings, medias embedded in another response — and costs no
extra call.

**The field is absent when the media publishes nothing.** A media never encoded, a live, a first
encoding still running: the key is simply not there. There is no `0` and no `null` to test, as
everywhere else in this API.

This is the one thing to get right about it, because the obvious test is wrong:

```js
// WRONG — files every media with nothing to play under "legacy"
if (media.source.encoding_version === 2) { /* current */ } else { /* legacy */ }
```

A missing field equals neither `1` nor `2`. Check presence first, and treat "nothing published" as
its own case:

```js
const v = media.source?.encoding_version;
if (v === undefined)   { /* nothing published yet — no pipeline to name */ }
else if (v === 2)      { /* current pipeline */ }
else                   { /* legacy encoder */ }
```

It describes what is published **today**, not what was asked for. A media queued for a re-encode
keeps answering `1` for as long as the legacy files are the ones being served, and switches to `2`
when the new ones take over.

What it buys you: until 5.46 the only way to know was `GET /medias/{media_id}/audio-tracks` and its
`encoding_v2` flag, one call per media. A whole catalog now sorts itself in one listing call:

```bash
curl -G "https://api.streamlike.com/medias" \
     -H 'X-Streamlike-Authorization: streamlikeAuth token="YOUR_KEY"' \
     --data-urlencode "range=0-99" \
     --data-urlencode "fields[]=id" \
     --data-urlencode "fields[]=source.encoding_version"
```

Two things that go with it:

- it is **read only**, and not an accepted input. If you edit a media by reading it and posting the
  whole object back, **strip it first** — like any field the form does not know, sending it answers
  `400 INVALID_FORM` with `UNKNOWN_FIELDS`,
- **it filters too, from API 5.48.** `GET /medias?source.encoding_version=2` keeps the medias
  published by the current pipeline, `1` the legacy ones, and leaving it out does not filter. The
  same parameter is on `GET /lives` and `GET /analytics/medias/{from}/{to}`. It reads the columns
  the returned field reads, so the value you ask for is the value that comes back — and a media
  publishing nothing is returned by **neither** value, so the two calls put together give you fewer
  medias than the unfiltered listing. Against a server older than 5.48 the listing cannot be
  restricted on it: read the field over a listing and sort client side.

The same value, under the same name, is on the webservice side as
`metadata.global.encoding_version`, in every media payload `media`, `playlist` and `related` return
— `references/webservices.md`.

## Waveform and peaks

API 5.44 and later. The player draws an audio media as an interactive waveform
(`references/player-embed.md`); the API holds its controls:

- **`waveform`** on the media (`POST /medias`, `PATCH /medias/{media_id}`, and in media
  responses): a nullable boolean forcing the skin on or off for one media. `null` — the default —
  follows the company preference, with one exception: an audio media carrying a cover **you**
  uploaded shows that cover rather than the skin. Set `waveform` to `true` on that media to get the
  skin anyway. Only meaningful on an audio media,
- **`peaks.files.index`** in media responses: URL of the peaks JSON sidecar, served for encoded
  audio medias. Format, per-track variants and what to do with it: `references/playback.md`,
- the **`waveform` and `waveform_color` company preferences** (`GET`/`PATCH
  /companies/preferences`): the account-wide default of the skin, and its accent color — six
  hexadecimal digits without `#` (e.g. `44B0A7`). The color also drives the covers the platform
  generates for audio medias uploaded without one.

Changing `waveform_color` is not free: the platform redraws, in the background, every generated
audio cover of the account. `GET /companies/preferences` tells you how many that is, in
`waveform_cover_count` (API 5.45) — an integer counting the audio medias whose cover was generated
from the waveform. Covers you uploaded yourself are never counted and never touched. Three things
about that field:

- it is **absent when the count is zero**. Read a missing key as "nothing to redraw", not as an
  error,
- it is **read only**. Posting your preferences back with it in the payload answers `400
  INVALID_FORM` / `UNKNOWN_FIELDS`, like any field the form does not know — send only the
  preferences you mean to change,
- it is served on `/companies/preferences` alone, because it costs a count over your medias.
  Preferences read from anywhere else do not carry it.

As with the audio-track endpoints, check `scripts/openapi_lookup.py fields /medias/{media_id}`
against the published description before relying on these: an older server does not know them.

## Endpoint map

160+ paths, grouped by tag. Explore with `scripts/openapi_lookup.py list --tag <name>`.

| Tag | What lives there |
| --- | --- |
| `Authentication` | Session and single-use tokens |
| `Me` | Current user, API keys, notifications, preferences |
| `Medias` | Medias and lives: CRUD, attachments, subtitles, chapters, interactions, audio tracks, covers, SCORM, social push, playback tokens |
| `Medias - Actions` | Bulk operations on a list of media ids: delete, duplicate, tag, keyword, playlist, visibility, security, re-encode, speech-to-text |
| `Medias - Misc` | Creators, languages, custom field and custom action templates |
| `Organization` | Playlists, tags, keywords, views |
| `Integration` | Player settings (`pid`), skins, logos, WebTV profiles, tracking accounts |
| `Security` | IP restrictions, referrer restrictions, webservice referrers |
| `Analytics` | Playbacks, audience, engagement, storage, transfer, encoding, greenhouse gas |
| `Jobs` | Encoding pipelines and jobs |
| `Streamout` | Scheduled broadcast channels |
| `Streamlink` | Short URLs bound to a media |
| `Social` | Linked YouTube / Dailymotion accounts |
| `Identity` | Users, groups, company preferences |
| `Hibernation` | Archived medias and their actions |
| `Helpdesk`, `Resources`, `Ftp`, `Tools` | Tickets, reference lists, FTP files, short URLs |

## Endpoints an integration reaches for first

| Goal | Call |
| --- | --- |
| Create a media with its file | `POST /medias` (multipart) |
| Publish / unpublish | `PATCH /medias/{media_id}` with `visibility.state` = `online`, `offline`, `archived` |
| Put medias in a playlist | `POST /medias/{media_ids}/actions/organization/playlist` |
| Reorder a playlist | `POST /organization/playlists/{playlist_id}/order` |
| Grant a viewer access to a protected media | `POST /medias/{media_id}/token` |
| Add subtitles or chapters | `POST /medias/{media_id}/subtitles/{language_id}`, `…/chapters/{language_id}` |
| Follow an encoding | `GET /pipelines`, and `GET /medias?encoded=1` to know what is playable |
| Add an audio track | `POST /medias/{media_id}/audio-tracks/{language_id}` |
| Replace the video, keeping the tracks | `POST /medias/{media_id}/video/replace` |
| Read audience | `GET /analytics/playback/{from}/{to}`, `GET /analytics/engagement/{media_id}/connections/{from}/{to}` |

## SDKs

`https://github.com/Streamlike/php-api-sdk` wraps this API for PHP. It saves the token handling and
the multipart plumbing; the semantics above still apply.
