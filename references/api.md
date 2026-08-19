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
| Follow an encoding | `GET /pipelines`, `GET /jobs/{job_id}/log` |
| Read audience | `GET /analytics/playback/{from}/{to}`, `GET /analytics/engagement/{media_id}/connections/{from}/{to}` |

## SDKs

`https://github.com/Streamlike/php-api-sdk` wraps this API for PHP. It saves the token handling and
the multipart plumbing; the semantics above still apply.
