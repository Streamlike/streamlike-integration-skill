# Webservices (`/ws/*`)

The read path of the platform. Fast, cacheable, made to drive video interfaces. Base URL in
production:

```
https://cdn.streamlike.com/ws/<service>
```

Every service takes its parameters in the query string and answers `f=json` (default) or `f=xml`.

The OpenAPI description lists a `POST` form for each service, but the production host only serves
`GET` — a `POST` to `cdn.streamlike.com/ws/*` answers `404` (checked August 2026). Build query
strings, and keep them within the usual URL length limits: that constrains how many values you can
pass to the repeatable filters below.

## The 15 services

| Service | What it returns | Needs IP whitelisting |
| --- | --- | --- |
| `playlists` | Every online playlist of a company | no |
| `playlist` | The medias of one or several playlists, paginated and filtered | no |
| `media` | Everything about one media | no |
| `related` | Medias sharing keywords with a given media | no |
| `languages` | Languages present in the online catalog | no |
| `countries` | Countries attached to the online catalog | no |
| `nowplaying` | How many viewers are watching a media right now | no |
| `resume` | Last position seen by a `user_token` on a media | no |
| `vote` | Stores a rating for a media | **yes, and it cannot be waived** |
| `manifest` | The media manifest: every encoded file and rendition | **yes** |
| `rss` | mRSS 2.0 feed | no |
| `podcast` | Podcast feed | no |
| `videositemap` | Google video sitemap | no |
| `qr` | PNG QR code pointing at a media | no |
| `getStreamlikeVersion` | Platform version | no |

`media` and `rss` are explicitly exempt from referrer/IP checks and can be called from a browser.
The others should be called server-side: they take the `company_id`, which addresses your whole
catalog.

## Paging and sorting — read this before writing a loop

Three details cost people an afternoon each:

- **`page` is an offset, not a page number.** `pagesize=10&page=10` returns items 10 to 19;
  `page=1` returns items 1 to 10. To walk a playlist ten by ten, increment `page` by `pagesize`,
- **`sortorder` takes `up` or `down`**, not `asc`/`desc`. A wrong value answers `404`,
- **the default `pagesize` is 10.** Raise it deliberately; the platform documentation asks
  integrators not to use very large values (`pagesize=999`) on every page view. Cache instead.

`orderby` values differ per service:

| Service | `orderby` |
| --- | --- |
| `playlist`, `rss` | `id`, `name`, `duration`, `vote`, `hit`, `lastplaybackdate`, `creationdate`, `lastupdateddate`, `lastupdatedfiledate`, `releasedate`, `position` |
| `playlists` | `id`, `name`, `creationdate`, `position` |

`position` follows the manual order set in the back office, which is what a curated playlist
expects.

## Errors

**The webservices answer `404` with an HTML error page** — for an unknown media, an unknown
parameter value, a service that requires an IP you have not whitelisted, or a typo in a parameter
value. There is no JSON error envelope.

Consequences for your code:

- check the HTTP status before parsing,
- check that the body is JSON before handing it to a parser; an HTML page means "rejected", not
  "empty",
- when a call that used to work starts answering `404` in production only, suspect IP whitelisting
  first.

## `playlist` — the catalog workhorse

```
GET /ws/playlist?playlist_id=PLAYLIST_ID&pagesize=20&page=0&f=json
```

One of `playlist_id`, `view_id` or `company_id` is required. Several playlists are read at once by
repeating the parameter — `playlist_id[]=ID1&playlist_id[]=ID2` — and the response merges them
(`metadata.size` covers the union). The `|` separator works on `videositemap`, not here.

| Parameter | Effect |
| --- | --- |
| `playlist_id` / `view_id` / `company_id` | The source of the medias |
| `page`, `pagesize` | Offset and count (see above) |
| `orderby`, `sortorder` | Sorting (see above) |
| `query`, `search_fields[]` | Full-text search. Fields: `id`, `name`, `description`, `credits`, `keywords`, `customs`, `transcription`, `permalink`, `subtitle` |
| `lng` | Restrict to a language |
| `country` | Restrict to a country |
| `encoded` | Keep only medias whose encoding is finished |
| `multiple_audio` | `1` keeps only multi-track medias, `0` only single-track ones, absent does not filter. Webservices 5.20 and later — earlier servers accept it and ignore it |
| `not_media_ids[]` | **Exclude specific medias** — repeat the parameter, one id per occurrence. `metadata.size` is corrected accordingly, so paging stays consistent |
| `not_playlist_ids[]`, `not_view_ids[]` | Exclude whole playlists or views |
| `not_languages[]`, `not_countries[]` | Exclusions by language or country |
| `forceplaylist` | Keeps the playlist order over the requested sorting |

Response shape:

```json
{"playlist": {
  "metadata": {"playlist_id": "…", "name": "…", "language": "fr",
               "size": 152, "total_duration": 31386},
  "medias": [ {"media": { … same shape as /ws/media … }} ]
}}
```

`metadata.size` is the size of the **whole** playlist, not of the page — use it to drive paging.

## `media` — everything about one media

```
GET /ws/media?media_id=MEDIA_ID
GET /ws/media?permalink=PERMALINK
```

```json
{"media": {
  "metadata": {
    "global": {"media_id", "name", "type", "permalink", "status", "description", "transcript",
               "credits", "duration", "ratio", "fps", "creation_date", "release_date",
               "lastupdated_date", "lastplayback_date",
               "is_360", "is_multiple_audio", "is_tokenized", "has_password",
               "is_downloadable", "is_secured"},
    "share": {"universal_url"},
    "customization": {"cover": {"url", "thumbnail_url", "thumbnaillarge_url",
                                "thumbnailextralarge_url"},
                      "mosaic": "…storyboard image…",
                      "board": {"small_url", "large_url"}},
    "subtitles": [{"subtitle": {"language_id", "url": {"dfxp", "vtt", "srt", "m3u8"}}}],
    "language_ids": [{"language_id": "fr"}],
    "playlists": [{"playlist": {"playlist_id", "name", "type", "position"}}],
    "keywords": {"standard_keywords": [{"standard_keyword": "démo"}]},
    "geolocation": {"zoom_level": 1}
  },
  "statistics": {"media_access", "rating_hits", "rating_totalvalue"},
  "html5_sources": [{"html5_source": {"type": "streamlike_html5", "manifest": "…m3u8…"}}]
}}
```

Fields worth knowing:

- `global.ratio` is the aspect ratio — feed it to your responsive wrapper
  (`padding-top: 100 / ratio %`),
- `global.duration` is in seconds,
- `global.is_tokenized`, `has_password`, `is_secured` tell you whether a plain player URL will
  play; see `references/security.md`,
- `global.is_multiple_audio` marks medias carrying several audio tracks,
- `statistics.media_access` is the playback counter, `rating_hits` / `rating_totalvalue` the
  ratings collected through `vote` (average = `rating_totalvalue / rating_hits`),
- `html5_sources[].html5_source.manifest` points at the media's file manifest — a JSON index of
  every encoded file, not an `.m3u8`. `references/playback.md` explains how to go from there to a
  playable URL.

Blocks are omitted rather than emptied: a media without subtitles has no `subtitles` key at all,
one without keywords no `keywords` key. Text values, on the other hand, come back as empty strings.
Test for both.

## `playlists`

```
GET /ws/playlists?company_id=COMPANY_ID&pagesize=50
```

Returns the online playlists, each with `playlist_id`, `name`, `description`, `language`,
`total_duration`, `view_position` and its podcast metadata. Use `view_id` to restrict the list to a
view — the platform's way of publishing a subset of the catalog to one front end.

## `related`

```
GET /ws/related?media_id=MEDIA_ID&pagesize=6
```

Medias sharing at least one keyword with the source media. Empty when the media carries no
keywords — a common surprise on catalogs where keywords were never filled in. `view_id` restricts
the pool.

## `nowplaying`, `resume`, `vote`

```
GET /ws/nowplaying?media_id=MEDIA_ID
GET /ws/resume?media_id=MEDIA_ID&user_token=YOUR_VIEWER_TOKEN
GET /ws/vote?company_id=COMPANY_ID&media_id=MEDIA_ID&value=5
```

- `nowplaying` returns the count of concurrent viewers, for a live badge or a "trending" ribbon,
- `resume` returns the last position seen by that `user_token`, so an app can offer "resume where
  you left off". The token is your own identifier for a viewer, and the same value must be passed
  to the player as `user_token=` for positions to be recorded in the first place,
- `vote` stores a rating from 0 to 5. **Its IP protection cannot be lifted**, and the platform
  makes it your responsibility to prevent multiple or automated votes — rate-limit and deduplicate
  in your backend before calling it.

## `manifest`

```
GET /ws/manifest?media_id=MEDIA_ID
```

Returns the full description of the encoded files of a media: renditions, bitrates, audio tracks,
subtitle tracks. Requires a whitelisted IP, so it is a backend-only call. `references/playback.md`
covers what to do with it, and the lighter routes that need no whitelisting.

## Practical advice from the platform documentation

- one call per need: do not call `media` for each entry of a list that `playlist` already returned,
- cache server-side when a page needs several calls,
- do not force a language (`lng`) when the metadata was never translated: you will get an empty
  catalog,
- significant deviation from these practices can lead to the account being restricted.
