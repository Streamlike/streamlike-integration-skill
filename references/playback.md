# Playback: streams, tracks and native players

Most integrations should embed the player (`references/player-embed.md`) and stop reading here: it
already handles adaptive streaming, tracks, subtitles, resume, reporting and browser quirks. Drive
the streams yourself only when the player cannot be embedded — a native mobile player, a set-top
box, a media pipeline.

## Three ways to reach the files

**1. The player.** `https://cdn.streamlike.com/play?med_id=…` — everything included.

**2. A direct file URL, resolved by the platform.** A redirect endpoint picks the best encoded file
for a target size:

```
https://cdn.streamlike.com/html5/{type}/media_id/{media_id}/width/1280/height/720
https://cdn.streamlike.com/html5/{type}/permalink/{permalink}
```

`{type}` is `hls`, `idevicev2`, `idevicev1`, `mp4`, `mp4low`, `webm` for video, `mp3` or `aac` for
audio. The endpoint answers `302` to the chosen file on the CDN. Without `width`/`height` it
returns the largest rendition — which for `hls` means one rendition, not the adaptive master.

**3. The file manifest.** `/ws/media` returns
`html5_sources[].html5_source.manifest`, the URL of a JSON index of every encoded file:

```json
{"mp4":       [{"globalbitrate": 1408, "width": 2090, "height": 1962, "url": "//cfcdn…/x_1280_720….mp4"}],
 "mp4low":    [ … ],
 "idevicev2": [{"globalbitrate": 0, "url": "//cfcdn…/idevicev2/index.m3u8"},
               {"globalbitrate": 320, "width": 240, "height": 176, "url": "//cfcdn…/….m3u8"}],
 "idevicev1": [ … ]}
```

Read it like this:

- `idevicev2` is the HLS group, `idevicev1` the older one, `mp4` / `mp4low` progressive files,
- **the entry whose `globalbitrate` is `0` is the adaptive master** (`index.m3u8`). That is the URL
  to hand to a native player; the others are single renditions,
- URLs are protocol-relative (`//cfcdn…`): prefix `https:`,
- `width` and `height` on a rendition are encoder-side values, not the display resolution — read
  the resolution from the HLS master if you need it exactly.

`/ws/manifest?media_id=…` returns the same information through the webservice, and needs a
whitelisted IP. The manifest URL from `/ws/media` does not, which usually makes it the easier
route.

## Inside the HLS master

```
#EXTM3U
#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="fr",LANGUAGE="fr",URI="/c/…/subtitles/fr/….m3u8"
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=1503232,RESOLUTION=1024x576,SUBTITLES="subs"
….m3u8?sltoken=
```

- subtitle tracks are declared as `EXT-X-MEDIA` with their language,
- variant URIs carry `?sltoken=` — empty for an open media, filled for a protected one. Keep the
  query string when you rewrite URLs, or playback stops at the first segment,
- some URIs are relative to the CDN root rather than to the manifest. Resolve them against the
  manifest URL, and test with a player that is strict about it.

Two pitfalls that cost real debugging time:

- **never pin a player to an audio-only variant** when you mean to show video. A media can publish
  one, and a player parked on it plays sound with no picture — and reports no video progress,
- an adaptive player left to itself starts low and climbs. If your app measures "is it playing" by
  bitrate, measure playback position instead.

## Multiple audio tracks

A media carrying several audio languages is flagged `metadata.global.is_multiple_audio` in
`/ws/media`, and `/ws/playlist?multiple_audio=1` filters the catalog on it.

- in the player, `audio_lng=en` selects a track, and the `-ad` suffix its audio description:
  `audio_lng=en-ad`,
- in a native player, the tracks are in the HLS master as `EXT-X-MEDIA:TYPE=AUDIO` entries with
  their `LANGUAGE` — select by language code, not by index; the order is not a contract,
- server side, `GET /medias/{media_id}/audio-tracks` lists the declared tracks and the API can add,
  replace, rename or promote them — see `references/api.md`. `GET /medias/{media_id}` also returns
  `source.audio_tracks` for a read-only view, on a single media only,
- per-track management needs a media produced by the current encoding pipeline. To know which
  medias those are without a call each, read `source.encoding_version` over a listing (API 5.46) —
  `2` is the current pipeline, `1` the legacy one, and an **absent** field means the media publishes
  nothing yet. `references/api.md` spells out why that absence matters,
- those endpoints need API 5.31 (5.37 for `source.audio_tracks`) and the `multiple_audio` filter
  webservices 5.20. Check `scripts/openapi_lookup.py show …` against the published description
  before relying on them: an older server answers `404`, or accepts the filter and ignores it.

## Subtitles and transcripts

`/ws/media` returns each subtitle track in four formats:

```json
"subtitles": [{"subtitle": {"language_id": "fr",
   "url": {"dfxp": "…", "vtt": "…", "srt": "…", "m3u8": "…"}}}]
```

- `vtt` for a browser `<track>`, `m3u8` for HLS, `srt` for downloads, `dfxp` for legacy tooling,
- the player displays them on its own; `c` toggles them, `subtitle=fr` forces a language,
  `subtitle=fr-cc` its closed-caption variant, `subtitle=0` disables them,
- tracks produced by speech-to-text also expose a word-level file, which is what
  `generateWords()` from the JS SDK renders as a live transcript.

## Waveform peaks

An encoded audio media publishes a peaks sidecar next to its other assets — the amplitude
silhouette the player's waveform skin draws (`references/player-embed.md`). It is plain public
JSON you can consume for your own rendering:

```json
{"version": 1, "count": 2000, "peaks": [0, 4, 18, 63, …]}
```

- amplitudes are integers `0..100` spread over the whole duration; `count` mirrors `peaks.length` —
  2000 buckets, fewer only when the source holds fewer samples,
- `GET /medias/{media_id}` returns the sidecar URL as `peaks.files.index` (API 5.44, encoded audio
  medias only). The file lives on the media's asset tree, under `…/medias/{media_id}/peaks/peaks.json`,
- a multi-track media publishes one sidecar per track, named by track token (`peaks/en.json`,
  `peaks/en-ad.json`) beside the default `peaks.json`; on medias produced by the current encoding
  pipeline, the file index also lists an `audio` array whose entries each carry their `peaks_url`,
- on a token-protected media the player fetches the sidecar through a tokenized URL, exactly as it
  does for the storyboard mosaic,
- an audio media encoded before the feature has no sidecar: expect a `404` and skip the drawing —
  that is what the player does. Re-encoding the media produces one.

## Live and Streamout

- a **live** channel plays through the same player with `live_id=STREAM_NAME`. The viewer can
  always rewind a little: the player exposes whatever the HLS playlist holds, and a live keeps
  about **100 seconds** behind the live edge. A live created with `live[dvr]=true` keeps about
  **45 minutes** instead — that is what the DVR is. The API default is `false` since API 5.51.
  The `live_dvr` embed parameter is accepted but the current player does not read it,
- a **Streamout** is a scheduled broadcast — a playlist played on a timetable — embedded with
  `str_id=STREAMOUT_ID`. Several player parameters do not apply to it (the table in
  `references/player-embed.md` has a column for this),
- `/ws/nowplaying?media_id=…` gives the concurrent viewer count, for a live badge.

## Downloads

`download=1` on the player shows a download button for the highest quality; an integer caps the
bitrate of the downloadable file. Availability also depends on the media being marked downloadable
(`metadata.global.is_downloadable`, set through the API or the back office).
