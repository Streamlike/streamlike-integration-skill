# Analytics: counting playbacks and engagement

The Streamlike player reports everything by itself. A custom or native player reports nothing
unless you make it — which is the most common cause of "the console says nobody watches our
videos".

## Counting a playback from your own player

One `GET` per playback, when playback actually starts:

```
https://cdn.streamlike.com/o.k?m=MEDIA_ID&t=TIMESTAMP&s=hls&p=myapp
```

| Parameter | Required | Meaning |
| --- | --- | --- |
| `m` | yes | `media_id` |
| `t` | recommended | Cache buster: a timestamp or random number |
| `s` | recommended | Stream type played: `mp4` or `hls` |
| `p` | no | Name of your player, to tell sources apart in the console |
| `u` | recommended | Viewer id — the same value you pass as `user_token` elsewhere, or a client fingerprint. Without it the playback is counted, but not as a playback of a player: it is left out of the playback ratio (see below) |
| `l` | no | Audio track heard when playback starts, as a track token: `fr`, `en`, `fr-ad` for an audio description. Omit it on a media with a single, undeclared audio track |
| `us` | no | Where the traffic comes from, as your own label (`newsletter-october`, `partner-site`); the Streamlike player sends the `utm_source` of its URL here. Takes the place of the referrer in the referrer statistics grouped by page. Up to 100 characters |
| `str` | no | Streamout id, when the media is played inside a streamout |

Fire it on the first `playing` event, once per playback, and unbind afterwards — every call counts
as a view.

## Counting an impression from your own player

From API 5.72 — check the published description first — the platform also counts **impressions**:
a media loaded into a player, played or not. The Streamlike player sends them by itself; its play
page announces the address in the `impression_url` meta. A player of your own sends one `GET` each
time a **VOD** media becomes the one it shows — page load, playlist step, media switch — without
waiting for playback. Never for a live, nor inside a streamout: both start on their own, so an
impression there would only mirror the playback, and the Streamlike player sends none (API 5.74):

```
https://cdn.streamlike.com/i.k?m=MEDIA_ID&t=TIMESTAMP&p=myapp&u=USER
```

| Parameter | Required | Meaning |
| --- | --- | --- |
| `m` | yes | `media_id` |
| `t` | recommended | Cache buster: a timestamp or random number |
| `p` | no | Name of your player |
| `u` | recommended | Viewer id, the same value as `u` on `o.k` |
| `r` | no | URL of the embedding page, URL-encoded |

One call per media shown, not per page: a playlist that loads three media sends three. Do not send
it again when the same media is replayed, or the ratio drops. And send `o.k` with `u` for the
playbacks of that same player, or the ratio reads zero: only those are counted against impressions.

## Reporting engagement from your own player

Engagement is the ratio between the average duration played per visit and the total length of the
media. It can exceed 1 when a viewer replays parts. To feed it, report **the segments actually
watched** to `eng.k`:

```
https://cdn.streamlike.com/eng.k?m=MEDIA_ID&d=137&t=hls&q=720&p=myapp
  &u=USER&s=SESSION&f=FINGERPRINT&ts=1529597356&rs=0&re=57
```

| Parameter | Required | Meaning |
| --- | --- | --- |
| `m` | yes | `media_id` |
| `d` | yes | Total media duration, seconds |
| `t` | yes | Stream type: `hls`, `mp4`, `mp3` |
| `q` | yes | Video height being played, pixels |
| `p` | yes | Player name |
| `ts` | yes | Client timestamp at the end of the segment, POSIX seconds |
| `rs` | yes | Segment start, seconds, between 0 and `re` |
| `re` | yes | Segment end, seconds, between `rs` and `d` |
| `s` | no | Session id, unique per player display |
| `u` | no | User id — the same value you pass as `user_token` elsewhere |
| `f` | no | Client fingerprint |
| `l` | no | Audio track heard over the segment, as a track token (`fr`, `en`, `fr-ad`). Omit it on a media with a single, undeclared audio track |

Call it at short, regular intervals so an abrupt close loses almost nothing, and again on every
seek, since a jump ends the current segment and starts another. Overlapping segments are expected
and are what makes replays visible. A change of audio track ends the current segment the same way:
a segment is always heard in one language, so the per-language figures of a multi-track media add
up.

## Identifying a viewer: `user_token`

Pass the same `user_token` for a given viewer, everywhere:

- to the player: `&user_token=…` (up to 64 characters, your own value),
- to `eng.k` as `u`,
- to `/ws/resume?media_id=…&user_token=…` to read back the last position seen.

That is what turns anonymous counts into per-viewer figures — resume, per-viewer engagement
(`GET /analytics/userstats/{media_id}/{user_token}/{from}/{to}`), and token statistics
(`GET /analytics/tokenstats/{from}/{to}`).

Choose the value carefully: it is a pseudonymous identifier of a person. Use an internal account id
or a random per-account value, never an email address or anything readable, and document it in your
privacy notice.

## Ratings

`/ws/vote?company_id=…&media_id=…&value=0..5` stores a rating — **0 to 5**, `0` the worst and `5`
the best, from webservices 5.20; before that `0` was rejected, quietly, with a `200` carrying
`res: false`. A value outside the range still is. `/ws/media` returns
`statistics.rating_hits` and `statistics.rating_totalvalue`; the average is their quotient, and
`rating_hits` is `0` on a media nobody rated, so guard the division.

The service requires a whitelisted IP that cannot be waived, and the platform explicitly leaves
vote deduplication and abuse prevention to you: keep a "this user already voted" record in your own
storage, and rate-limit before calling.

For a like/dislike feed, the rating is a reasonable transport (`5` for a like), but the durable
state — who liked what — belongs in your database. The platform stores an aggregate, not a per-user
history.

## Reading figures back, server side

The API exposes the same numbers as the console, all on a `{from}/{to}` date range:

| Endpoint | Figures |
| --- | --- |
| `GET /analytics/playback/{from}/{to}` | Playbacks per type |
| `GET /analytics/playback/top/popular/{from}/{to}` | Most watched media |
| `GET /analytics/playback/location/{countries\|cities\|continents}/{from}/{to}` | Geography |
| `GET /analytics/playback/client/{devices\|browsers\|os}/{from}/{to}` | Devices |
| `GET /analytics/playback/referers/{from}/{to}` | Where playbacks come from |
| `GET /analytics/engagement/{media_id}/connections/{from}/{to}` | Engagement timeline of one media |
| `GET /analytics/engagement/{media_id}/qualities/{from}/{to}` | Engagement per video quality |
| `GET /analytics/viewership/{from}/{to}` | Viewership |
| `GET /analytics/medias/{from}/{to}` | Per-media table, sortable on its figures (API 5.74); accepts `filter` (API 5.68), same syntax as `GET /medias` — `references/api.md` |
| `GET /analytics/viewers/{from}/{to}` | Per-viewer table, one row per `user_token`, sorted and paged (API 5.74) |
| `GET /analytics/userstats/{media_id}/{user_token}/{from}/{to}` | One viewer on one media |
| `GET /analytics/languages/{media_id}/{playbacks\|listening\|transfer}/{from}/{to}` | Audience of a multi-track media per audio language (API 5.55) |
| `GET /analytics/impressions/{from}/{to}` | Impressions of the player, its playbacks and the playback ratio (API 5.72) |
| `GET /analytics/transfer`, `/storage`, `/encoding`, `/greenhousegas` `/{from}/{to}` | Consumption, including CO₂e |
| `GET /analytics/catalogs/{from}/{to}` | Catalog duration held, as a daily snapshot |
| `GET /analytics/company/billable` | Consumption since the start of the contractual term, against the allowance |
| `GET /analytics/company/users/{from}/{to}` | Your back-office accounts and your catalogue by creator (API 5.74) |

`/ws/media` also carries a cheap playback counter (`statistics.media_access`) if all you need is
"how many views" next to a thumbnail.

### Breaking in API 5.30: `duration_total` in `/analytics/company/billable` changed unit

**If you read `data.catalog.{date}.duration_total`, your figures change the day API 5.30 reaches
production.** It used to be raw seconds. It is now **hours of weighted catalogue**, rounded to two
decimals. Nothing was renamed and nothing moved: the same key answers a different unit. Code that
plots it drops by three orders of magnitude without raising anything, and code that divides it by
3600 to get hours is now wrong twice over.

Why it changed: `catalog_limit`, at the root of the same response, has always been stated in hours
of weighted catalogue — that is the unit contracts are written in. `duration_total` was the figure
you were meant to measure against it, in seconds. One response, two units, and the comparison
everybody actually wanted was silently wrong. They are now the same unit and compare as they are:

```js
const week  = body.data.catalog['2026-08-31'];
const used  = week.duration_total;      // hours of weighted catalogue, e.g. 412.75
const cap   = body.catalog_limit;       // same unit, e.g. 500
const ratio = cap ? used / cap : null;  // catalog_limit is absent when there is no cap
```

The old value divided by 3600 is *not* the new one, only its order of magnitude: the weighting
discounts part of the catalogue. Online and offline **video** counts in full, archived video for a
fifth, **audio** for a tenth, archived audio for a fiftieth.

**The eleven raw durations beside it stay in seconds.** `duration_online`, `duration_offline`,
`duration_archived`, `video_duration_total`, `audio_duration_total` and the six
`{video,audio}_duration_{online,offline,archived}` are unchanged — they are the terms the weighting
is computed *from*. So `duration_total` is deliberately **neither their sum nor in their unit**, and
one `catalog` entry now carries two units on purpose. Do not add it to them, and do not rescale them
to match it.

**`GET /analytics/catalogs/{from}/{to}` is not affected.** Its own `duration_total` is still raw
seconds. The same key name means seconds in that report and weighted hours in `billable`: only the
billing one was aligned on the contractual unit.

### Four habits of these reports

They all answer the same way, and each of these breaks code written against a normal JSON API.

**An empty report is the JSON array `[]`, not an object.** When nothing matched the period there is
no `data` key to reach into, and no empty `data` either — the whole body is `[]`. So
`response.data[companyId]` throws instead of returning nothing. Test the body first:

```js
const body = await res.json();
const rows = Array.isArray(body) ? {} : body.data;   // [] means "nothing matched"
```

Three endpoints are exempt and always answer a `data`: `/analytics/company/logins/{from}/{to}`,
`/analytics/company/users/{from}/{to}` and
`/analytics/userstats/{media_id}/{user_token}/{from}/{to}`.

**The keys are the values.** A report is an object keyed by encrypted company id, then by date,
then by country code, browser name or storage kind. Where the published description writes
`data.{company_id}.{date}.{mode}`, the braces mark a level whose key you *read*, not a field name
you look up. Iterate; never index by a name you decided in advance.

**Absent means none.** Nothing is sent as `null` or as `0` when there is nothing to say — the key
is simply not there. A day nobody watched has no date key, a country nobody played from has no
country key. Two consequences: the series have holes, so **lay down your own calendar before
plotting one**, and a test written as `if (count === 0)` never fires, because there is no `count`
to compare.

**`aggregation` changes the shape, not just the grouping.** It replaces the per-company level with
the literal key `__all__`, and on several reports it also removes a level: `aggregation=total` on
encoding, storage, transfer and greenhouse gas puts the figure directly under the date, where the
detailed answer has one entry per kind. The same reading code cannot serve both modes, and the
`companies` metadata block is never sent alongside an aggregated report.

**And `subtotal` is not offered everywhere.** Sixteen reports take an `aggregation` parameter at
all, and all sixteen accept `total`. Only **four** also accept `subtotal`, the roll-up that keeps
one line per company:

| Report | `total` | `subtotal` |
| --- | --- | --- |
| `GET /analytics/playback/{from}/{to}` | yes | yes |
| `GET /analytics/storage/{from}/{to}` | yes | yes |
| `GET /analytics/transfer/{from}/{to}` | yes | yes |
| `GET /analytics/greenhousegas/{from}/{to}` | yes | yes |
| the twelve others | yes | **no** |

The twelve that refuse it are `catalogs`, `encoding`, `engagement/{media_id}/qualities`, the three
`playback/client/*`, the three `playback/location/*`, `playback/players`, `playback/referers` and
`impressions`.
Asking one of them for `subtotal` answers `400` with `INVALID_AGGREGATION`. Note that only the main
`playback` report takes it — the narrower playback breakdowns beside it do not.

Every other analytics endpoint — `viewership`, `medias`, `tokenstats`, the two `top/*`,
`userstats`, `live/streams`, `engagement/{media_id}/connections`, the three `languages/{media_id}/*`
and the `company/*` reports — has no `aggregation` parameter at all.

Since API 5.30 the published description of `aggregation` lists only the roll-ups the endpoint it
sits on actually offers, so it is worth reading per endpoint rather than assumed.

### A selection of media in one call

From API 5.74, `media_ids` restricts a report to a list of media and sums them up server side.
Do not loop over `media_id` and add the answers yourself: one call over the selection gives the
same figures, and a distinct-viewer count (`viewer_count` in `viewership`) cannot be added up
across calls anyway. It is accepted by `/analytics/playback` and its `players`, `referers`,
`location/*`, `client/*` and `top/*` reports, by `transfer`, `viewership` and `live/streams`.

```
GET /analytics/playback/2026-09-01/2026-09-30?aggregation=total&media_ids[]=0123456789abcdef&media_ids[]=fedcba9876543210
```

- repeat the parameter, or send the ids comma-separated (`media_ids=a,b,c`), up to 10,000,
- every id must exist and be visible to your key, and fall inside `company_id` when you pass it:
  one bad id refuses the whole request with `400 INVALID_MEDIAIDS`, rather than answering a
  partial total,
- with `playlist_ids`, `tag_ids` or `keyword_ids`, only the media matching both are kept; a
  selection that matches nothing answers `[]`, not the whole catalogue,
- the per-company level stays: two media of two companies answer two keys under `data`, unless
  you ask for `aggregation=total`.

A list that does not fit in a URL goes in a body: the same reports answer to `POST` on the same
URL, with the same parameters as a JSON object (`Content-Type: application/json`). That `POST`
writes nothing and stays available during a maintenance window, like the `GET`. Do not repeat
`media_ids[]` a thousand times in a query string or a form-encoded body: past 1,000 parameters the
request answers `400 TOO_MANY_PARAMETERS`. A JSON array, or one comma-separated value, has no such
limit.

```js
const res = await fetch(`${api}/analytics/viewership/2026-09-01/2026-09-30`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-Streamlike-Authorization': auth },
  body: JSON.stringify({ media_ids: selection }),   // an array of encrypted media ids
});
```

API 5.74 also opens `playlist_ids`, `tag_ids` and `keyword_ids` on `viewership`, and makes
`live/streams` apply them: they were accepted and ignored there, so a client that already sent one
now gets fewer lives.

### A table in one call

From API 5.74, a dashboard that lists its catalogue or its audience fills the table with one call,
sorted and paged by the API, instead of one call per row sorted on its side.

**One row per media: `GET /analytics/medias/{from}/{to}`.** The listing of `GET /medias`, with
its filters (`filter` included) and its `range`, each row carrying its figures over the period:
`playbacks`, `viewed_duration`, `viewer_count`, `session_count`, the two averages,
`unique_viewed_duration`, `replay_duration`, and the bytes served as `transit_total`,
`transit_vod`, `transit_live`, `transit_hibernation`, `transit_downloaded` and
`transit_other`. Unlike the other reports, **every row carries every column, 0 included**: a
media nobody watched is a row of zeroes, not a missing key — except `avg_bitrate` and
`sobriety_score`, which have no meaning without a second watched and are then absent.

```
GET /analytics/medias/2026-09-01/2026-09-30?sorts[]=playbacks|desc&sorts[]=name|asc&range=0-49&fields[]=id&fields[]=name&fields[]=playbacks&fields[]=viewed_duration
```

- these columns sort, and must come first: a catalogue field after them breaks the ties, one
  written before them answers `400 INVALID_SORTS`,
- such a sort reads the whole filtered catalogue, up to 10,000 media; beyond, `400
  TOO_MANY_MEDIAS_TO_SORT` asks you to narrow the filter,
- `fields[]` keeps to what you name, figures included.

**One row per viewer: `GET /analytics/viewers/{from}/{to}`.** Every `user_token` that played or
watched something over the period, with `playbacks`, `viewed_duration`, `session_count`,
`average_duration_per_session`, `unique_viewed_duration` and `replay_duration`. It takes the
filters of the playback reports (`media_id`, `media_ids`, the label filters, `company_id`), sorts
with `sorts[]=column|direction` (by default `viewed_duration|desc`) and pages with `range`, in the
envelope of a listing: `data`, `total_count`, `returned_count`, and the two `returned_*_index`
when the page is not empty. It answers to `POST` with a JSON body too, like the reports above.

A playback recorded without a user token belongs to no viewer: the rows add up to less than
`/analytics/playback` when your integration does not always pass one.

**Counting, without listing.** `/analytics/viewership` gives `viewer_count` and, from API 5.74,
`media_count`: how many distinct media were watched over the period, under its filters. Do not
download `/analytics/tokenstats` to count: it returns every media and token pair at once, which
runs long on a large audience. It takes `media_ids` and the label filters since API 5.74, and the
viewers of one media, page by page and with their figures, are `/analytics/viewers?media_id=…`
— its rows with `playbacks` above 0 are exactly the tokens `tokenstats` lists for that media.

**What the catalogue weighs.** From API 5.74 the weighting of `catalog_limit` (video in full,
archived video × 0.2, audio × 0.1, archived audio × 0.02, a live not at all) is applied by the
platform wherever you need it, so do not copy it into your code:

- per media, the `billable_duration` and `billable_duration_archived` columns of
  `/analytics/medias`, in weighted seconds; their difference is what archiving the media saves,
  and both sort,
- for the catalogue as it stands, `/analytics/company/stats` gives `billable_duration` and a
  `repartition` by type then state, each with `count`, `duration` and `billable_duration`,
- day by day, every entry of `/analytics/catalogs` carries `billable_duration`.

Divide weighted seconds by 3600 to compare with `catalog_limit`. The allowance itself, with
`term_begin` and `transit_limit`, stays on `/analytics/company/billable`, which needs the
`ANALYTICS_BILLING` role.

**How sober the delivery is.** `/analytics/sobriety/{from}/{to}` (API 5.74) divides the bytes of
the streamed renditions (vod, live, and media woken from hibernation) by the seconds watched: `avg_bitrate`, in kbit/s, and the
`sobriety_score` it earns, A below 1,000 kbit/s, then a letter per 1,000 up to E from 4,000 — the
`scale` comes with the answer, so do not hard-code it. It takes `media_id`, `media_ids`, the label
filters and `company_id`; per media, the same figures are the `avg_bitrate` and `sobriety_score`
columns of `/analytics/medias`. Before `modes_complete_from` (also in the answer) part of the vod
bytes was filed under other, so a period reaching back before that day reads a bitrate too low.
The period is not cut for you.

**Adding up the transfer.** `/analytics/transfer` keeps its historical keys by default, where
`__total_other__` repeats the sum of `other` and `__other__`. Ask `breakdown=normalized` and every
bucket holds exactly `vod`, `live`, `hibernation`, `downloaded`, `other` and `total`, 0 included,
which add up without counting anything twice.

**How many finished a media.** With `media_id`, on a media that has a duration,
`/analytics/viewership` gives `completed_viewer_count`, the viewers who saw more than 90 % of it
at least once, and `completion_distribution`, the viewers by tenth of the media seen: key `"0"`
for less than 10 %, key `"90"` for 90 % or more, all ten keys present. They agree with the
`completion_rate` of `/analytics/userstats/{media_id}/*/{from}/{to}`, which you no longer need to
download whole — on a media watched by thousands, it is the slow call. Both are absent without
`media_id` and on a live.

**Your users, without listing them.** `/analytics/company/users/{from}/{to}` (API 5.74, role
`ANALYTICS_COMPANY_ABSTRACT`) replaces paging `/users` and the whole catalogue to draw a users
tab. Under `users`: `total`, `enabled`, `disabled`, `new_in_period` and `new_in_previous_period`
(the period of the same length just before), `active_in_period` (distinct users who signed in, where
`/analytics/company/logins` counts sign-ins), `created` and `evolution` keyed by every UTC day of
the period, 0 included, and `recency`, the accounts by how long ago they last signed in: `day`,
`week`, `month`, `quarter`, `year`, `older`, `never`, which add up to `total`. Under `creators`:
the media by the user who created them, `count`, `duration` and `count_in_period`, most prolific
first, plus `total`, `in_period` and `without_creator`. It covers your company only, never its
subsidiaries. A deleted account is in no `users` figure but `active_in_period`, and its media stay
under `creators` with the name it last had.

### Live sessions: the latest ones, or all of them

`GET /analytics/live/streams/{from}/{to}` lists the broadcasting sessions of each live media,
grouped under its encrypted id, oldest first within a media. From API 5.78, `max_result` (1 to
9999) keeps only the most recent sessions of the period, counted across all the live media, still
grouped by media:

```
GET /analytics/live/streams/2026-10-01/2026-10-31?max_result=10
```

- a screen that shows the last sessions passes it, instead of loading the whole history and
  cutting on its side,
- an export that wants every session leaves it out: without it, every session of the period comes
  back, the CSV included (before API 5.78 the report stopped silently at 9999),
- any other value answers `400 INVALID_FORM` with `INVALID_MAXRESULT`,
- the media are not ordered under `data`: iterate and read each list, do not rely on key order.

### Buckets and bounds

The timed reports take `period` to set the width of their buckets, and with it the format of the
keys: `2026-10-05` for `day` and `week` (the Monday), `2026-10` for `month`, `2026-Q4` for
`quarter` (API 5.74), `2026` for `year`. A trend since a media was created is one call with the
width you show, not a regrouping of days on your side.

The engagement reports (`viewership` and the two `engagement/{media_id}/*`) answer
`available_since` (API 5.74): the day of the oldest engagement figure the platform still holds. A
period starting earlier reads nothing before it. Clamp your date pickers to that day rather than
to a retention you wrote down: it is measured, so it follows the platform.

### One media, per audio language

From API 5.55, the audience of a multi-track media can be read per audio track, on three reports that share one shape:

| Endpoint | Figure |
| --- | --- |
| `GET /analytics/languages/{media_id}/playbacks/{from}/{to}` | Plays, by the track selected when the play was recorded |
| `GET /analytics/languages/{media_id}/listening/{from}/{to}` | Seconds actually spent on each track, replays counted again |
| `GET /analytics/languages/{media_id}/transfer/{from}/{to}` | Bytes served for the audio rendition of each language |

The answer is `data.__all__.{date}.{language}` — `[]` when nothing matched — the language being the
track token (`fr`, `en`, `fr-ad`), at most 30 per bucket, the largest first. The media is the one
in the path, so there is no company level and no `aggregation`: `__all__` is the only roll-up, and
`aggregation`, `company_id` or `max_result` answer `400 UNKNOWN_FIELDS`. `period`, `format=csv`
(columns `date,language,` then `count`, `seconds` or `bytes`) and, on the first two,
`user_token` apply. A live, or a media of another company, answers `400 INVALID_MEDIAID`.

Two things to build in:

- **`__unknown__` is a bucket, not a track.** It gathers what was recorded before the player sent
  the language, and the audio files whose name carries none — on a media promoted from single to
  multi-track, its whole earlier life. Add it to the total and never list it as a language,
- **your own player feeds these figures only if it sends `l`** on `o.k` and `eng.k` (see the two
  parameter tables above). Without it, every play of a multi-track media lands under `__unknown__`.

The transfer report reads the language from the file name pulled, so it also counts what a
third-party player downloads; the two others count only what reported itself.

### Impressions and the playback ratio

From API 5.72, `GET /analytics/impressions/{from}/{to}` sets the impressions of the Streamlike
player against the playbacks it started. Each bucket is an object, not a number:

```json
{"data": {"48c6eab371919246": {
   "2026-10-12": {"impressions": 4, "playbacks": 2, "playback_ratio": 0.5},
   "2026-10-13": {"impressions": 0, "playbacks": 3}
 }},
 "measured_from": "2026-10-12"}
```

`data.__all__.{date}` replaces the company level with `aggregation=total` (no `subtotal`). The
filters are those of `GET /analytics/playback/{from}/{to}` plus `streamout_id`, without `source`
nor `max_result`. CSV gives one row per figure: `company_id,date,indicator,value`.

Four things to build in:

- **`playbacks` here is not `GET /analytics/playback`.** Only playbacks of a player are counted:
  YouTube, Dailymotion, podcast and RSS playbacks have no impression to be set against and are left
  out, and so is an `o.k` sent without `u`. Do not mix the two figures in one table,
- **`playback_ratio` is absent when the bucket has no impression** — not `0`, not `null`. It is
  `playbacks / impressions` rounded to four decimals, a fraction (`0.5` is 50 percent), written
  without decimals when whole (`1`), and it can exceed `1` when a viewer replays without reloading,
- **`measured_from` is the day impressions started being recorded**, platform-wide. A bucket older
  than it has playbacks and `impressions: 0`: show the ratio as unknown there, never as zero. It is
  absent from CSV and from an empty `[]` answer,
- **past days keep their totals, not their detail** (API 5.73). Every night the impressions of the
  previous UTC day are folded into one count per company and media. The totals per day, company and
  media do not move, but a folded day no longer knows the viewer, the streamout nor the hour: with
  `user_token` or `streamout_id` it reads no impression, and with an hourly `period` all of them sit
  at noon UTC. Filter impressions by viewer or streamout for the current day only; for anything
  older, read the totals.

### Dividing transfer by watch time or impressions

An average bitrate or a volume per playback divides `GET /analytics/transfer/{from}/{to}` by
`GET /analytics/viewership/{from}/{to}` (or by the playbacks of `/analytics/impressions`). The
sources do not arrive at the same pace:

- **the bytes served for recorded media reach `transfer` up to about 18 hours late**, while watch
  time, playbacks and impressions are current to within the hour. Over a period ending less than 18
  hours ago the ratio reads too low. End the period of every report at the same bound, 18 hours
  before now or earlier — `{to}` takes a date-time such as `2026-11-04T14:00:00Z`, inclusive,
- **on a past day, cut at midnight UTC**, not inside the day: its impressions are folded at noon
  (see above), so a bound before noon drops all of them and one after keeps all of them, against
  part of the day's playbacks,
- **average bitrate = (`vod` + `live` bytes) × 8 / `viewed_duration`**, in bits per second, over
  the same period and filters: the quality the players actually pulled, weighted by watch time. It
  can differ from the bitrates the media were encoded at, and reads too low over a period starting
  before `modes_complete_from` (below),
- **playback ratio = playbacks / impressions**, both from `/analytics/impressions`: our player only,
  podcast, RSS and YouTube playbacks are not counted, and it is unknown before `measured_from`.

### Four figures that are not what they look like

- **`data.transfer` in `GET /analytics/company/billable` is a running total.** Each week already
  contains every week before it, and the last entry is your consumption to date. One week alone is
  the difference between two consecutive entries — **summing them counts the same bytes many times
  over.** In the same response, `greenhousegas` is the one series that really is per week and may
  be added up,
- **catalog and storage figures are snapshots**, not amounts added that day. What you grew over a
  week is the difference between its two ends, never a sum,
- **the transfer breakdown by mode is only complete from the day `modes_complete_from` names.**
  Every JSON answer of `GET /analytics/transfer/{from}/{to}` carries that day at the root of the
  response. In a bucket older than it, part of the bytes served for recorded media sits under
  `other` instead of `vod`, because the stats pipeline did not yet recognise the file names of the
  v2 encodings. Bucket totals are right at every date, so a consumption or billing total is
  unaffected; what reads too low is anything built on `vod` and `live` alone — an average bitrate,
  a volume per playback — by a share that varies from one day to the next. No factor repairs it:
  over a period that reaches back before that day, derive the figure from the bucket totals, or
  leave it out,
- **the engagement ratios of `/analytics/userstats/…` are fractions, not percentages.** `0.0377`
  means 3.77 percent. They are rounded to four decimals, and `viewing_ratio` goes above `1` when a
  viewer replays. In the CSV form the column is headed `percentage`, but the values in it are the
  same unscaled fractions.

### CSV is not `text/csv`

Wherever `format=csv` is offered — the analytics reports and `/streamouts/{streamout_id}/medialist`
alike — the body comes back as **`application/vnd.ms-excel`**, never `text/csv`, whatever the file
extension says. Branch on the parameter you sent, not on the content type. The CSV form also drops
the `companies` metadata block that the JSON form carries.

## Knowing where the plays come from: `utm_source`

Browsers send the page that embeds the player as a referrer, but their default referrer policy
(`strict-origin-when-cross-origin`) cuts it down to the origin: every play from
`https://www.example.com/news/article-42` counts as `https://www.example.com/`. Only an iframe carrying `referrerpolicy="unsafe-url"` sends the full
URL, and few pages do.

Put the information in the player URL instead:

```
https://cdn.streamlike.com/play?med_id=MEDIA_ID&utm_source=newsletter-october
```

The value is a label you choose, not necessarily a URL: one per campaign, mailing, partner or page
family. The player reports it with the playback (`us` in the `o.k` beacon), and the referrer
statistics grouped by page (the back office, and the API with `referrer_detail=page` below) count
that play under `utm_source=newsletter-october` instead of the origin. The referrer is still
recorded; only the grouping changes. Plays without `utm_source` keep the
referrer. The value is trimmed and cut to 100 characters. Only `utm_source` is read: other UTM
parameters (`utm_medium`, `utm_campaign`) are ignored.

From API 5.74 a play whose page sent no referrer at all (a direct link, a browser or an app that
strips it) is counted under `__unknown__`, in both modes, so the referrers add up to the play
count; before, it was counted nowhere.

In the API that grouping is a choice: pass `referrer_detail=page` to
`GET /analytics/playback/referers/{from}/{to}`. The default, `referrer_detail=full`, returns each
referrer exactly as the browser sent it, query string included, and does not read `utm_source`, so
code written against it keeps its figures. With `page`, the entries are pages: the query string
and the fragment are dropped (one entry per `?fbclid=…` or `?gclid=…` no longer pushes the real
pages out of the list), the host is lowercased without a trailing dot, a bare origin ends with `/`,
plays on a page Streamlike serves itself (the player page, the back-office preview, a short link)
fall under the literal key `__streamlike__`, and plays carrying a `utm_source` fall under
`utm_source=<label>`.

## Third-party tracking

Tracking accounts (Google Analytics and others) are configured in the back office and attached to
media, so playback events reach your own analytics without any code in your integration. The API
manages them under `/trackings` and
`POST /medias/{media_ids}/actions/integration/tracking`.

## Where the numbers will not match

- a media embedded with a non-Streamlike player and no `o.k` call is invisible in the console,
  while its traffic still shows in transfer consumption — that gap is also how bandwidth theft is
  spotted,
- viewers on mobile networks change IP, so IP-based restrictions and geography can disagree,
- playbacks are counted on playback start; engagement on watched segments. Comparing the two counts
  as if they measured the same thing leads nowhere.
