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

## Reading a response — the rules that hold everywhere

Every response is an object with exactly **one root key**, named after the service: `media`,
`playlist`, `playlists`, `nowplaying`, and `medias` for `related`.

**An empty value is a missing key, not a `null` and not an empty object.** The payload is swept
before it is sent: every `null` is dropped, and so is every object or array the sweep leaves empty,
recursively. `false`, `0` and `""` are values and survive — `"is_tokenized": false` and
`"duration": 0` come back as such, and a field the back office holds as an empty string comes back
empty rather than absent. So test for both, and never for `null`.

Two lines that look right and are not:

```js
if (media.metadata.global.has_sound === false) { … }   // misses every media where it is absent
media.metadata.subtitles.length                        // throws: no key without subtitles
```

**Listings keep their key when they match nothing** — that is the one exception. `related` answers
`{"medias":[]}` and `playlists` answers `{"playlists":[]}`, so you always get a valid document.
`playlist` is the odd one out: it drops the `medias` key entirely and leaves `metadata.size` at
`0`. Test `size`, not the presence of the list.

**Dates** are `YYYY-MM-DDThh:mm:ss±hhmm`, UTC — the offset carries **no colon**, so this is not the
RFC 3339 spelling and a few strict parsers reject it. **Durations** are whole seconds.
**Identifiers** are 16 hexadecimal characters and opaque: never parse one, never assume an order
between two. **URLs are protocol-relative** (`//cdn…`) except covers, storyboards and manifests,
which come back absolute in `https:`.

**Only online medias are ever returned**, which is why `metadata.global.status` always reads
`online`. There is nothing to filter on it.

### XML costs more than a parameter

`f=xml` renders the same values under the same names, but three things change:

- **booleans become `0` and `1`.** `<is_360>0</is_360>` is `false`. Do not confuse them with the
  fields that really are numbers: `<encoding_version>1</encoding_version>` means "the legacy
  encoder", not "true",
- **there are no arrays.** A list of one and a list of ten differ only by their number of children,
  so an XML client must always iterate, never read a single node,
- **a list entry with no name of its own is wrapped in `<value>`**, since webservices 5.26. Most
  lists name their entries and are unchanged: `country_ids` holds `<country_id>`, `subtitles` holds
  `<subtitle>`. Search excerpts and manifest renditions have no such name, and they used to be
  poured flat into the parent — which produced an unparsable document on `playlist` with a `query`,
  and lost the grouping of the renditions on `manifest`. Both are covered below, and the `manifest`
  one changes a document you may already be reading.

Text is wrapped in `CDATA`, so `&` and quotes come through unescaped.

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
| `encoding_version` | `2` keeps only the medias published by encoding-v2, `1` only those published by the legacy encoder, absent does not filter. A media publishing nothing carries no version and is returned by neither value; an unknown value answers `404`. **Webservices 5.25 and later** |
| `not_media_ids[]` | **Exclude specific medias** — repeat the parameter, one id per occurrence. `metadata.size` is corrected accordingly, so paging stays consistent |
| `not_playlist_ids[]`, `not_view_ids[]` | Exclude whole playlists or views |
| `not_languages[]`, `not_countries[]` | Exclusions by language or country |
| `forceplaylist` | Keeps only the medias filed in at least one playlist, dropping those filed nowhere. Redundant with `playlist_id`, which already implies it. Accepts `true`/`false` or `1`/`0`. **Webservices 5.22 and later** — before that, `0` and `1` were read inverted |

Response shape:

```json
{"playlist": {
  "metadata": {"playlist_id": "…", "name": "…", "language": "fr",
               "size": 152, "total_duration": 31386},
  "medias": [ {"media": { … same shape as /ws/media … }} ]
}}
```

`metadata.size` is the size of the **whole** playlist, not of the page — use it to drive paging. It
is always there, `0` included; `medias` is not, so read `size` first.

Ask for **exactly one** `playlist_id` and the fields of that playlist are merged into `metadata`
next to `size`: `playlist_id`, `name`, `description`, `language`, `total_duration`, `cover_url`,
`podcast` and your public playlist custom fields. Ask for a company, a view, or several playlist
ids at once and `metadata` holds nothing but `size` — there is no single playlist to describe.

### Searching

A `query` adds `metadata.highlight` to the medias where the search actually matched, and to those
alone. Its keys are the fields that matched, its values the matching excerpts with the matched
words wrapped in `<em>`. Two shapes live in it: a text field such as `name.stemmed` or
`description` gives **a list of strings**, a matched subtitle gives `subtitle.<language>` holding
**a list of objects** with a `timecode` and a `text`. Read the keys as a map; do not hard-code
them.

**XML works with a `query` from webservices 5.26.** Each excerpt is wrapped in a `<value>`, so a
text field gives a run of `<value>` strings and a matched subtitle gives one `<value>` per hit,
holding its `timecode` and its `text` together. Before 5.26 the excerpts came out as `<0>`, `<1>`,
which are not legal element names, and that broke **the whole document**, not just the highlight
block. Against a server older than 5.26, ask for JSON when you pass a `query`.

## `media` — everything about one media

```
GET /ws/media?media_id=MEDIA_ID
GET /ws/media?permalink=PERMALINK
```

```json
{"media": {
  "metadata": {
    "global": {"media_id", "name", "type", "permalink", "status", "description", "transcript",
               "credits", "duration", "ratio", "fps", "has_sound",
               "creation_date", "release_date",
               "lastupdated_date", "lastupdatedfile_date", "lastplayback_date",
               "encoding_version",
               "is_360", "is_multiple_audio", "is_tokenized", "has_password",
               "is_downloadable", "is_secured"},
    "share": {"universal_url"},
    "validity_period": {"begins", "ends"},
    "audio_tracks": [{"audio_track": {"language_id", "kind", "label", "default"}}],
    "chapters": [{"chapter": {"language_id", "url"}}],
    "attachments": [{"attachment": {"description", "filename", "url"}}],
    "live": {"stream_name", "begins_at", "ends_at"},
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
- `global.encoding_version` says which encoder produced the files the media publishes: `2` for the
  current pipeline, `1` for the legacy one (webservices 5.23 and later). See the warning below
  before comparing it,
- `statistics.media_access` is the playback counter, `rating_hits` / `rating_totalvalue` the
  ratings collected through `vote` (average = `rating_totalvalue / rating_hits`),
- `global.lastupdatedfile_date` is the last **successful encoding**, where `lastupdated_date` is the
  last change to the metadata. Renaming a media moves the second and not the first — so the file
  date is the one to key your own file cache on,
- `subtitles[].subtitle.url` is **an object, not a string**: one URL per format (`dfxp`, `vtt`,
  `srt`, `m3u8`, and `words` for word-level timings). `chapters[].chapter.url`, sitting right next
  to it, **is** a plain string. The asymmetry is real and long-standing,
- `subtitles[].subtitle.language_id` is not always a bare language code: a suffix types the track,
  and `fr-cc` means closed captions in French as opposed to plain `fr` subtitles. Do not truncate it
  to two letters, or the two become one,
- `attachments[]` lists **public attachments only**. A media may well carry files that never appear
  here,
- `html5_sources[].html5_source.manifest` points at the media's file manifest — a JSON index of
  every encoded file, not an `.m3u8`. `references/playback.md` explains how to go from there to a
  playable URL.

Absence works as *Reading a response* describes: a media without subtitles has no `subtitles` key
at all, one without keywords no `keywords` key, and the four `customization.cover.*` sizes appear
or disappear together. Guard the container before walking into it.

### Your custom fields land in `global`, and can shadow it

The public custom fields of a media are merged **flat into `metadata.global`, next to the standard
fields and after them**. A custom field named `campaign` appears as `metadata.global.campaign`.
Private custom fields are never returned, and a field with no explicit visibility counts as public.

Because they are merged in last, **a custom field named like a standard one replaces it.** Name one
`duration` and `metadata.global.duration` stops being the duration of the media. Give your custom
fields names of your own — a prefix is the cheapest protection — and never iterate over `global`
assuming everything in it is either standard or yours.

### No `html5_sources` at all? Check the account before the encoding

The block is absent in three cases worth telling apart: the media publishes nothing yet, the media
is a live, or **the account carries the option that hides file URLs**. On such an account no media
ever returns `html5_sources`, however well encoded. The option removes that block and nothing else
— covers, storyboards, subtitles, chapters and attachments keep coming. If you find no manifest on
every single media, ask Streamlike support whether the option is on rather than hunting for an
encoding problem.

### Telling a live apart

`global.type` reads `video`, `audio` or `live`, and the `metadata.live` block is present on a live
and on nothing else. **Read the type first**, because several fields exist for one kind and not for
another: `fps`, `has_sound`, `encoding_version`, `is_multiple_audio`, `html5_sources`, `subtitles`
and `chapters` are all absent on a live, `duration` is always `0` and means nothing, and
`share.universal_url` addresses the stream name rather than the media — take that URL as it comes
instead of rebuilding it from `media_id`.

### `encoding_version` is absent, not `1`, when nothing is published

The omission rule above has a sharp edge on `global.encoding_version`. A media that publishes
nothing — never encoded, a live, a first encoding still running — has no `encoding_version` key at
all. It is not `0` and not `null`: there is no pipeline to name yet.

So this test is wrong, and wrong silently:

```js
// WRONG — files every media with nothing to play under "legacy"
if (media.metadata.global.encoding_version == 2) { /* current */ } else { /* legacy */ }
```

Check the key is there before comparing it, and give "nothing published" its own branch. The value
describes what is served today, not what was asked for: a media queued for a re-encode keeps
answering `1` until the new files take over.

Two more details:

- in XML (`f=xml`) it comes out as `<encoding_version>1</encoding_version>`. It is a **number**,
  unlike the flags sitting next to it — `is_360`, `is_multiple_audio`, `is_tokenized` are booleans
  rendered as `0` or `1`. Here, `1` means the legacy encoder, not "true",
- **it is returned everywhere a media is, and `playlist` filters on it from webservices 5.25.**
  `media`, `playlist` and `related` serialize their medias identically, so `global.encoding_version`
  is in all three responses. `/ws/playlist?encoding_version=2` keeps the medias published by the
  current pipeline, `1` the legacy ones, and leaving it out does not filter — a media publishing
  nothing carries no version and is returned by neither value. An unknown value answers `404`,
  which is the webservice habit and differs from the API, whose filters drop what they do not
  recognise. `media` answers about one media you name and `related` returns encoded medias only, so
  neither takes the parameter. The API filters on it too, from 5.48 (`references/api.md`).

## `playlists`

```
GET /ws/playlists?company_id=COMPANY_ID&pagesize=50
```

Returns the online playlists, each with `playlist_id`, `name`, `description`, `language`,
`total_duration`, `view_position`, its podcast metadata and your public playlist custom fields. Use
`view_id` to restrict the list to a view — the platform's way of publishing a subset of the catalog
to one front end.

Three details that catch people:

- **`view_position` is a string**, `"0"`, `"1"`, `"2"`. Sort on it numerically, or eleven lands
  between one and two. Compare it with `metadata.playlists[].playlist.position` on a media, which
  *is* an integer: two different things, typed differently,
- **the cover keys are not named like a media's.** The object is `cover_url`, and inside it the
  keys are `cover`, `thumbnail`, `large`, `extralarge` and `podcast` — no `_url` suffix, unlike
  `customization.cover.thumbnail_url` on a media,
- **there is no total count here.** Paginate until you get a short page; `playlist` is the service
  that gives you a `size`.

## `related`

```
GET /ws/related?media_id=MEDIA_ID&pagesize=6
```

Medias sharing at least one keyword with the source media, each carrying the same media block as
`/ws/media` plus `metadata.relation_weight` — an integer counting the keywords in common, which is
what the results are ranked on. Empty when the media carries no keywords, a common surprise on
catalogs where keywords were never filled in. `view_id` restricts the pool.

Three things this service does that the others do not:

- **the source media is never in its own results.** No need to filter it out,
- **only encoded medias come back.** A media still waiting for its first encoding is skipped
  whatever its keywords, and so is a live — expect no `type: "live"` here. If you use `related` to
  build a "more like this" strip, that is the reason a live never appears in one,
- **there is no total count**, unlike `playlist`.

## `nowplaying`, `resume`, `vote`

```
GET /ws/nowplaying?media_id=MEDIA_ID
GET /ws/resume?media_id=MEDIA_ID&user_token=YOUR_VIEWER_TOKEN
GET /ws/vote?company_id=COMPANY_ID&media_id=MEDIA_ID&value=5
```

**`nowplaying`** answers `{"nowplaying":{"count":42}}` and nothing else. That count is the
**distinct viewers who reported playback activity on the media in the last two minutes**. The
window is fixed and no parameter changes it, so a viewer who paused three minutes ago is gone while
one who closed the tab thirty seconds ago is still counted: treat it as a live gauge with a
two-minute tail, not as a count of open players. It counts viewers rather than sessions — the same
viewer in two tabs counts once. Polling faster than the window buys you nothing.

**`resume`** answers `{"resume":{"timecode":0}}`, an integer number of seconds, and it is the one
service on this page that **never omits its field**. "Nothing known" is reported as `0`, which is
also what a viewer who watched the first second and stopped gets — three situations answer `0` and
you cannot tell them apart: the token was never seen, the viewer watched more than a month ago, or
they really are at the beginning. Two things follow:

- **the window is one month.** A viewer who left a media half-watched forty days ago comes back as
  a fresh start,
- **the value is not where playback stopped.** It is the furthest second reached during the most
  recent session. A viewer who jumps to ten minutes, comes back to two and closes the page resumes
  at ten. Offer the choice rather than seeking silently.

The token is your own identifier for a viewer, and the same value must be passed to the player as
`user_token=` for positions to be recorded at all. It is also the only identity checked, so anyone
holding a token reads that viewer's position: mint one per person and keep it unguessable.

**`vote`** answers `{"vote":{"res":true}}` — a single boolean, no vote id, no updated average, no
count. **The accepted range is 0 to 5**, `0` the worst grade and `5` the best. `value=0` was
rejected before webservices 5.26, which contradicted the description of the parameter itself; it is
stored like any other grade now, and only a value below `0` or above `5` answers `res: false`.
Rejection is quiet, because `res: false` covers both "the value was out of range" and "the write
failed on our side", and both answer **200**. A `404` means something else entirely — a missing or
malformed parameter, or a media that does not belong to the company you named.

In XML that boolean renders as `0` or `1`, and `"0"` is truthy in most languages, so a retry loop
written against the XML answer never retries:

```js
if (String(res) === '1' || res === true) { done(); } else { retry(); }
```

**Its IP protection cannot be lifted**, each call adds a vote, nothing deduplicates the caller and
there is no way to withdraw one — rate-limit and deduplicate in your backend before calling. Read
the resulting rating back from `/ws/media`.

## `manifest`

```
GET /ws/manifest?media_id=MEDIA_ID
```

Returns the full description of the encoded files of a media: renditions, bitrates, audio tracks,
subtitle tracks. Requires a whitelisted IP, so it is a backend-only call. `references/playback.md`
covers what to do with it, and the lighter routes that need no whitelisting.

The single field `manifest` is **a copy of the media's `index.json` as the encoder wrote it**. There
is no fixed schema: the sections are named after what was actually produced and they differ between
the legacy encoder and the current one. Read it defensively.

- an **empty object** — `{"manifest":[]}` with a `200`, not a `404` — means the media has no
  manifest yet: never encoded, or a first encoding still running,
- **the numbers are not all of the same type.** The HLS master entry carries the JSON number `0` in
  `globalbitrate`, while renditions carry strings, because the generator reads them out of the file
  name. Cast before you compare, or `globalbitrate > 1000` matches nothing,
- legacy **audio** medias are shaped differently again: `manifest.mp3` and `manifest.aac` are single
  objects, not lists. Code that iterates every section as an array breaks on them,
- read audio-track languages from `manifest.audio[].language`, never out of a file name,
- passing a `token` rewrites **every field whose name contains `url`** and nothing else. Without a
  token, a media secured by token answers `404` rather than handing back untokenized URLs.

```js
const master = manifest.idevicev1.find(e => Number(e.globalbitrate) === 0);
```

**The XML rendering changed in webservices 5.26**, and it is the one change of that release that
can break code you already wrote. Each rendition of a section is now its own `<value>`. Before,
a section was a flat run of children — `globalbitrate` three times, `width` twice, entries not all
carrying the same fields — and nothing paired a `url` with its bitrate except counting positions.

```xml
<idevicev1>
  <value><globalbitrate>0</globalbitrate><url>…m3u8</url></value>
  <value><globalbitrate>518</globalbitrate><width>512</width><height>288</height><url>…</url></value>
</idevicev1>
```

**If you were counting positions, your path gains one step**: `idevicev1/value[2]/url` where you
had `idevicev1/url[2]`. JSON, the default, is unaffected, and it stays the form we recommend for
this service.

## `languages` and `countries`

```
GET /ws/languages?company_id=COMPANY_ID
GET /ws/countries?company_id=COMPANY_ID
```

The same shape — a single list, each entry holding one code — and they are what you build a filter
from, so the front only ever offers values the catalog actually has. Both keep their key when
empty: `{"language_ids":[]}`, `{"country_ids":[]}`.

**But the case differs.** `languages` answers `fr` and `countries` answers `FR`, in the same
account, on the same page. Normalise before feeding both into one lookup table — this is the
mistake these two services collect.

Two more things. The code counted is the **main language of a media**, the one field set on the
media itself: subtitle and audio-track languages are not in there, read `/ws/media` for those. And
**the criterion is that the media is encoded, not that it is online** — a media whose visibility
window has closed still contributes its language. Use these lists to build a selector, not to
decide what a visitor can watch.

## Practical advice from the platform documentation

- one call per need: do not call `media` for each entry of a list that `playlist` already returned,
- cache server-side when a page needs several calls,
- do not force a language (`lng`) when the metadata was never translated: you will get an empty
  catalog,
- significant deviation from these practices can lead to the account being restricted.
