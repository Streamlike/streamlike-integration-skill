# Changelog

Version numbers follow [semantic versioning](https://semver.org): the major digit moves when a
recipe or a rule that integrators depend on changes meaning, the minor when surface is added, the
patch for corrections that change nothing you would have written differently.

The same version is published to both distributions — the Claude skill and the Gemini gem — from
the same source.

## 3.1.0 — 2026-09-01

**Reads now answer during a planned maintenance window** (API 5.52). Streamlike closes the
platform for announced maintenance; until this version every endpoint answered `401` with
`API_OFFLINE` for the length of the window, reads included. Reads stay open now, so an
application that only lists or displays a catalogue no longer stops when we do.

Writes are unchanged: `POST`, `PATCH` and `DELETE` still answer `401 API_OFFLINE` and write
nothing. `GET /tools/shorturl` answers to `GET` but mints the short link, so it closes with the
writes. The webservices (`/ws/*`) were never concerned and still are not.

Two rules worth putting in your code, both in `references/api.md`:

- **`API_OFFLINE` is the one `401` worth retrying**, and it is told apart on the message, never on
  the status. Any other `401` means the credentials are the problem, and retrying with the same key
  will never fix it,
- **a listing read during a window can be short, and nothing in the answer says so.** Reindexing
  runs during maintenance, so a collection may return fewer items than it holds, with a `200` and a
  consistent `total_count`. Never reconcile a local store against a listing read during a window:
  what stopped appearing has not been deleted.

`cookbook/server-ingest.md` says what an ingest pipeline should do with a window — hold the queue,
drain it once it closes — and `references/feeds.md` flags the short-url call. Nothing written
against 3.0.0 breaks: the platform only opens what was closed, so code that treats every `401` as
fatal still works, it is merely more cautious than it needs to be.

Corrected in passing, and unrelated to windows: the collection wrapper example showed
`"degraded": false`. The platform never sends that — the key appears **only when it is true**, so
testing for `false` tests for something you will never receive. `degraded` means the full-text
backend was unavailable and your `search` was not applied, so the answer comes back **wider** than
you asked, not shorter.

## 3.0.0 — 2026-09-01

**A live is now created with the DVR off** (API 5.51). `POST /lives` used to store
`live[dvr]=true` when the field was omitted, while its description already said the default was
`false`. The behaviour now matches the words: omit the field and the live runs without a rewind
window.

If your integration creates lives and your viewers pause and rewind them, **send
`live[dvr]=true` at creation** — or set it afterwards with `PATCH /lives/{media_id}`, while the
live is not running. An integration that already sends the field, whichever value, is
unaffected. Existing lives keep the value they have stored, and `live.dvr`, returned on every
live response, tells you where each one stands.

The `live_dvr` player parameter is not a substitute: it shows or hides the DVR controls, but the
rewind window only exists when the live runs with the DVR enabled. `references/playback.md` and
the parameter table in `references/player-embed.md` now say so. Relying on the old default was
relying on an accident rather than a contract, but it is a behaviour change on a public
endpoint, hence the major digit.

## 2.5.0 — 2026-08-31

Encoding complexity comes back to the API, and it now does something. Nothing written against
2.4.0 stops working: this release only widens what is accepted and removes an error you could
receive.

- **`source[complexity]` is accepted again on `POST /medias` and `PATCH /medias/{media_id}`** (API
  5.50). An integer from `1`, a slide deck or a screencast, to `5`, fast motion or fine grain, `3`
  by default. It tells the encoder how hard the picture is to compress and moves the bitrate it
  aims for. Versions 5.31 to 5.49 dropped it because the encoder of the day ignored the value;
  that encoder reads it now. Out of range answers `400 INVALID_FORM` with
  `INVALID_SOURCE_COMPLEXITY`. The field never stopped being *returned* as `source.complexity`,
- **`POST /medias/{media_ids}/actions/complexity` accepts every video media again**, whichever
  pipeline published it. A media that answered `400 INVALID_GLOBAL_ACTION` with
  `INVALID_MEDIA_ENCODING_V2` now answers `200`, and **no endpoint returns that error code any
  more**. If you special-cased it, the branch is dead code — it was never part of this
  specification, so nothing changed shape,
- **Setting the complexity still encodes nothing**, on the field as on the bulk action: the value
  is stored and applies to the *next* encoding of that media. Nothing is re-queued behind your
  back and the files being served do not change. This was already true and stays true; it is
  written down now because the setting having an effect makes the question worth asking,
- **Bitrates reported for medias on the current pipeline are measured, not nominal.** They used to
  come from a table keyed on resolution; they are now what the encode actually spent. A simple
  screencast can report a small fraction of what a comparable media reported before — same
  picture, truer number. Nothing to change unless you compare bitrates across medias encoded
  before and after.

## 2.4.0 — 2026-08-26

Three behaviours this bundle described as permanent were defects, and they are fixed (webservices
5.26). A fourth correction is ours alone: a paragraph that told you not to cache something you can
cache. **Nothing written against 2.3.0 stops working** — the first three widen or repair what was
there — with one exception, spelled out below, which only reaches readers who ignored our own
advice.

- **`/ws/vote` accepts `value=0`.** The parameter has always been documented as an integer from 0,
  the worst, to 5, the best, and `0` was rejected anyway. It is stored like any other grade now.
  Outside `0..5` the answer is still `res: false` with a `200`. `references/webservices.md`,
  `references/analytics.md` and `cookbook/mobile-feed-app.md` said "1 to 5, not 0 to 5"; they no
  longer do,
- **`/ws/playlist?query=…&f=xml` returns a document that parses.** Search excerpts came out as
  elements named `<0>` and `<1>`, which are not legal element names, and that broke **the whole
  document**, not the highlight block alone. Each excerpt now sits in a `<value>`, and a matched
  subtitle keeps its `timecode` and its `text` together inside one `<value>`. You no longer have to
  fall back to JSON when you search,
- **`/ws/manifest?f=xml` changes shape, and this is the one item that may need work on your side.**
  A section such as `idevicev1` was a flat run of children: `globalbitrate` three times, `width`
  twice, entries not all carrying the same fields, so nothing paired a `url` with its bitrate
  except counting positions. Each rendition is now its own `<value>`. **If you were counting, your
  path gains one step**: `idevicev1/value[2]/url` where you had `idevicev1/url[2]`. JSON, the
  default, is untouched. The release stays minor because 2.3.0 told you not to read this service in
  XML at all, and this fix is what makes XML usable for it,
- **the `/ws/qr` image URL is stable, and you can cache it.** The description of `media_id` claimed
  that each call minted a new short link, so two codes drawn for the same media would not lead to
  the same place. That was never true: an existing short link is reused, and the same media at the
  same level and size gives back the same image. The `src` is served over `https` now, where a
  fresh code used to come back in `http` and be blocked as mixed content in a secure page. Nothing
  changed in the reuse itself — only the sentence that described it.

**Everything above that changes behaviour ships with webservices 5.26, which is not deployed
everywhere yet** — the short-link reuse is the exception, it has always worked that way. The
reference pages
name the version each behaviour belongs to, and `examples.md` presents the XML search as a call
whose answer depends on the server you point it at.

Two sentences written in 2.2.0 have also stopped being true, and both told you to do more work than
you have to. **`encoding_version` is a filter now**, on both surfaces: `GET /medias?source.encoding_version=2`
in the API (5.48, and the same parameter on `GET /lives` and `GET /analytics/medias/{from}/{to}`),
`/ws/playlist?encoding_version=2` on the webservice side (5.25). `references/api.md` said the
listing "cannot be restricted on it" and `references/webservices.md` said it was "a parameter
nowhere"; both now describe the parameter. Sorting a catalog by pipeline client side is no longer
the only way. A media that publishes nothing is returned by neither value, so asking for `1` and
`2` and adding them up gives you fewer medias than the unfiltered listing.

## 2.3.0 — 2026-08-26

Both public surfaces now describe what they **return**, not only what you send (API 5.47,
webservices 5.24). No behaviour changed anywhere; what changed is what you can know before you
write the code. This release carries over the part of it that makes an integration different.

The rule that runs through everything, now stated once in `SKILL.md` and in full in
`references/webservices.md`: **an empty value is an absent key.** Neither surface sends `null` or
`0` to mean "nothing here" — the key is gone, and a container the sweep leaves empty goes with it.
`false`, `0` and `""` are values and survive. The recipes were guarding covers and result lists
badly and now do it properly; `examples.md` shows the rule on a real demo media.

Analytics reports have four habits that break ordinary JSON code, all new in
`references/analytics.md`:

- **an empty report is the array `[]`**, so `response.data[companyId]` throws rather than returning
  nothing,
- **the keys are the values** — you iterate over company ids, dates and country codes rather than
  looking field names up,
- **a gap is a missing key, never a `0`**, so the series have holes: lay down your own calendar
  before plotting one,
- **`aggregation` changes the shape**, replacing the company level with `__all__` and removing a
  level on several reports. The same reading code cannot serve both modes.

Three figures that were being misread, and one content type:

- **`data.transfer` of `/analytics/company/billable` is a running total**: summing the weeks counts
  the same bytes many times over. Catalog and storage figures are snapshots, not amounts added,
- **the ratios of `/analytics/userstats/…` are fractions, not percentages** — `0.0377` is 3.77
  percent, even in the CSV column headed `percentage`,
- **a CSV answer is `application/vnd.ms-excel`**, never `text/csv`.

Four API responses that are not the shape you expect, now in `references/api.md`:

- **`GET /medias/{media_id}/sourceinfo` answers in two shapes** — wrapped once encoded, bare
  before. Test for `info` first,
- **`POST /medias/{media_id}/export/ftp` sends its nulls**, where `GET /pipelines/{pipeline_id}`
  omits the keys. Code shared between the two must test the value, not the key,
- **the `Content-Type` of a downloaded attachment lies**: anything outside a short list of
  extensions is served as `video/mpeg`. Use the name in `Content-Disposition`,
- **`GET /medias/{media_id}/audio-tracks` does send nulls**, unlike the rest of the API.

On the webservice side, `references/webservices.md` gains the response rules and the traps that go
with them: **your public custom fields are merged flat into `metadata.global` after the standard
ones**, so one named `duration` replaces the duration of the media; `nowplaying` counts distinct
viewers over a **fixed two-minute window**; `resume` never omits its value, answers `0` for three
different situations, reads back **the furthest second of the last session** rather than where
playback stopped, and looks back one month only; `vote` takes **1 to 5, not 0 to 5**, and refuses
quietly with a `200`; `related` never returns a live nor an unencoded media; `playlists` types
`view_position` as a **string**; a missing `html5_sources` on every media means the account hides
file URLs, not that the encoding failed. **Two calls must not be made in XML**: `playlist` with a
`query` produces a document that does not parse, and `manifest` loses the grouping of its lists.

`references/feeds.md` finally says what the feeds actually emit: **`enclosure/@length` carries a
duration in seconds**, where RSS expects a size in bytes, and its `url` is a page rather than a
file; the mRSS `<description>` has an `<img>` tag prepended to it; `videositemap` answers
`<error>No profile exists</error>` with an **HTTP 200** when the account has no WebTV profile, which
is how empty sitemaps get published; `podcast` guards on a category (404) and on a description and
link (400); the `qr` `src` comes back as `http://` and is blocked as mixed content until you rewrite
it.

## 2.2.0 — 2026-08-25

A media now says which encoder produced the files it publishes, on both public surfaces (API 5.46,
webservices 5.23):

- **`source.encoding_version`** in the API, **`metadata.global.encoding_version`** on the
  webservice side — in every media payload, so `media`, `playlist` and `related` all carry it. Same
  name, same integer, same meaning: `2` for the current encoding pipeline, `1` for the legacy
  encoder. It describes what is served today, not what was asked for,
- **read the warning before you compare it.** The field is *absent* — not `0`, not `null` — when the
  media publishes nothing at all: never encoded, a live, a first encoding still running. A test
  written as `if (encoding_version == 2) { … } else { … }` therefore files every unplayable media
  under "legacy", which is not what it is. `references/api.md` and `references/webservices.md` both
  spell it out,
- what it replaces: `GET /medias/{media_id}/audio-tracks` and its `encoding_v2` flag, one call per
  media. A whole catalog now sorts itself in a single listing call. It is **read only**, and it is
  a **parameter nowhere**: neither surface can filter a listing on it, so read it off the medias
  you already asked for and sort them yourself,
- `is_multiple_audio` is unchanged on both sides — it has been there since the multitrack release
  and this version adds nothing to it.

Catching up on API 5.45, released without a skill update:

- **`waveform_cover_count`** on `GET /companies/preferences`: how many audio medias of the account
  carry a cover generated from the waveform, hence get redrawn in the background the next time
  `waveform_color` changes. Absent when the count is zero, read only, and served on that endpoint
  alone: `references/api.md`,
- corrected, in the same breath: an audio media carrying a cover **you** uploaded shows that cover
  rather than the waveform skin, unless the media's `waveform` field says otherwise. This skill said
  the skin was on whenever a peaks file existed, which was too broad —
  `references/player-embed.md`.

Still described ahead of production: check the published OpenAPI description before relying on any
of these fields.

## 2.1.0 — 2026-08-25

Audio medias gain a waveform skin in the player, and the data behind it is public:

- the player displays an interactive waveform on audio medias that carry a peaks file — click or
  drag seeks, the cover comes back with `waveform=0`. Two new player parameters, `waveform` and
  `waveform_color`, and two CSS custom properties control it: `references/player-embed.md`,
- the peaks sidecar (`peaks/peaks.json`, one `{track}.json` per audio track) is plain public JSON
  an integration can render on its own; format and URLs in `references/playback.md`,
- API 5.44 exposes the controls: the `waveform` media field, `peaks.files.index` in media
  responses, and the `waveform` / `waveform_color` company preferences: `references/api.md`.

Described ahead of production, like the audio-track endpoints before it: check the published
OpenAPI description before relying on the API fields.

## 2.0.0 — 2026-08-23

**`forceplaylist` changes meaning on the `playlist` webservice** (webservices 5.22). It read
its numeric values inverted — `0` turned the filter on, `1` turned it off. They now mean what
they say: `1` and `true` keep only the medias filed in at least one playlist, `0` and `false`
do not filter.

Sending `true` or `false` changes nothing for you. Sending `0` or `1` **changes your result**:
if you had settled on a value by trial and error, it now does the opposite. The parameter is
rarely used and the old behaviour was a defect rather than a contract, but it is a behaviour
change on a public endpoint, hence the major digit.

## 1.2.0 — 2026-08-23

- **`forceplaylist` was described wrongly.** It does not keep the playlist order over the
  requested sorting; it keeps only the medias filed in at least one playlist. And its legacy
  numeric values are inverted — `0` turns the filter on, `1` turns it off. Send `true` or
  `false`. If you set `forceplaylist=1` expecting an ordering, you were getting neither.
- Every parameter of every webservice now carries a description in the published description
  (webservices 5.21). Two behaviours that were written nowhere are now stated: on `rss`, a
  `playlist_id` always wins over `query`; and `page` remains an offset in items, as this
  reference already said.

## 1.1.0 — 2026-08-23

- **Deleting a live is not open to customer accounts.** `DELETE /lives/{media_id}` requires a
  platform-scope role, and the bulk delete refuses a live too, with `MANDATORY_ROLE`. Stopping a
  live stays yours; removing it afterwards goes through Streamlike support. The endpoint always
  behaved this way and said nothing about it, which is what changed.
- Every parameter of every endpoint now carries a description and a type in the published
  descriptions, nested request-body fields included. Nothing moved in what the endpoints accept;
  `openapi_lookup.py` is simply worth reading now.

## 1.0.0 — 2026-08-23

First numbered release. The content had already been published; this is the point where it starts
being versioned, so an integrator can tell which state of the platform they are reading about.

- covers the three public surfaces: webservices, REST API, hosted player, plus the JS SDK,
  playback, security, analytics and feeds,
- carries the API surface as of API 5.38 and webservices 5.20 — the per-track audio endpoints and
  the `multiple_audio` playlist filter are described and flagged as not yet in production,
- adds a Gemini gem distribution alongside the Claude skill, built from the same files.
