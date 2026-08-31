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

Fire it on the first `playing` event, once per playback, and unbind afterwards — every call counts
as a view.

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

Call it at short, regular intervals so an abrupt close loses almost nothing, and again on every
seek, since a jump ends the current segment and starts another. Overlapping segments are expected
and are what makes replays visible.

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
the best, from webservices 5.26; before that `0` was rejected, quietly, with a `200` carrying
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
| `GET /analytics/playback/top/popular/{from}/{to}` | Most watched medias |
| `GET /analytics/playback/location/{countries\|cities\|continents}/{from}/{to}` | Geography |
| `GET /analytics/playback/client/{devices\|browsers\|os}/{from}/{to}` | Devices |
| `GET /analytics/playback/referers/{from}/{to}` | Where playbacks come from |
| `GET /analytics/engagement/{media_id}/connections/{from}/{to}` | Engagement timeline of one media |
| `GET /analytics/engagement/{media_id}/qualities/{from}/{to}` | Engagement per video quality |
| `GET /analytics/viewership/{from}/{to}` | Viewership |
| `GET /analytics/medias/{from}/{to}` | Per-media table |
| `GET /analytics/userstats/{media_id}/{user_token}/{from}/{to}` | One viewer on one media |
| `GET /analytics/transfer`, `/storage`, `/encoding`, `/greenhousegas` `/{from}/{to}` | Consumption, including CO₂e |
| `GET /analytics/catalogs/{from}/{to}` | Catalog duration held, as a daily snapshot |
| `GET /analytics/company/billable` | Consumption since the start of the contractual term, against the allowance |

`/ws/media` also carries a cheap playback counter (`statistics.media_access`) if all you need is
"how many views" next to a thumbnail.

### Four habits of these reports

They all answer the same way, and each of these breaks code written against a normal JSON API.

**An empty report is the JSON array `[]`, not an object.** When nothing matched the period there is
no `data` key to reach into, and no empty `data` either — the whole body is `[]`. So
`response.data[companyId]` throws instead of returning nothing. Test the body first:

```js
const body = await res.json();
const rows = Array.isArray(body) ? {} : body.data;   // [] means "nothing matched"
```

Two endpoints are exempt and always answer a `data`: `/analytics/company/logins/{from}/{to}` and
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

### Three figures that are not what they look like

- **`data.transfer` in `GET /analytics/company/billable` is a running total.** Each week already
  contains every week before it, and the last entry is your consumption to date. One week alone is
  the difference between two consecutive entries — **summing them counts the same bytes many times
  over.** In the same response, `greenhousegas` is the one series that really is per week and may
  be added up,
- **catalog and storage figures are snapshots**, not amounts added that day. What you grew over a
  week is the difference between its two ends, never a sum,
- **the engagement ratios of `/analytics/userstats/…` are fractions, not percentages.** `0.0377`
  means 3.77 percent. They are rounded to four decimals, and `viewing_ratio` goes above `1` when a
  viewer replays. In the CSV form the column is headed `percentage`, but the values in it are the
  same unscaled fractions.

### CSV is not `text/csv`

Wherever `format=csv` is offered — the analytics reports and `/streamouts/{streamout_id}/medialist`
alike — the body comes back as **`application/vnd.ms-excel`**, never `text/csv`, whatever the file
extension says. Branch on the parameter you sent, not on the content type. The CSV form also drops
the `companies` metadata block that the JSON form carries.

## Third-party tracking

Tracking accounts (Google Analytics and others) are configured in the back office and attached to
medias, so playback events reach your own analytics without any code in your integration. The API
manages them under `/trackings` and
`POST /medias/{media_ids}/actions/integration/tracking`.

## Where the numbers will not match

- a media embedded with a non-Streamlike player and no `o.k` call is invisible in the console,
  while its traffic still shows in transfer consumption — that gap is also how bandwidth theft is
  spotted,
- viewers on mobile networks change IP, so IP-based restrictions and geography can disagree,
- playbacks are counted on playback start; engagement on watched segments. Comparing the two counts
  as if they measured the same thing leads nowhere.
