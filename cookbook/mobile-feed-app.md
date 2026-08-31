# A phone app that scrolls, likes and dismisses

The brief: a vertical feed over a Streamlike playlist. Swipe to the next video, tap to like,
dismiss a video so it never comes back. This recipe maps that onto the platform, and says which
half you have to build yourself.

## What belongs where

| Concern | Where it lives |
| --- | --- |
| The catalog and its order | Streamlike playlist (or view) |
| Media metadata, covers, durations | `/ws/playlist`, `/ws/media` |
| Playback | Streamlike player in a WebView, or a native player on the HLS stream |
| "This user liked this video" | **Your database** |
| "This user dismissed this video" | **Your database** |
| Aggregate rating | `/ws/vote`, optional |
| Playback and engagement figures | Streamlike, automatically with the player; through `o.k` and `eng.k` if you play natively |

The platform stores a catalog, not per-user state. Likes and dismissals are yours to keep. That is
the single design decision this feature turns on — everything else follows.

## Architecture

```
  App  ──►  Your backend  ──►  cdn.streamlike.com/ws/*   (catalog, GET only)
                          ──►  api.streamlike.com        (only if you write to the platform)
   │
   └──► player iframe or HLS stream, straight from the CDN
```

The app never holds the `company_id` and never holds an API key: both address the whole account.
Your backend does, and it is also where per-user state lives.

Streams and player pages, on the other hand, are fetched directly by the device — proxying video
through your servers would cost you the bandwidth the CDN is there to absorb.

## 1. Fetch a page of the feed

```js
// backend, Express-style
app.get('/feed', async (req, res) => {
  const user = await authenticate(req);
  const offset = Number(req.query.offset || 0);
  const pageSize = 10;

  const url = new URL('https://cdn.streamlike.com/ws/playlist');
  url.searchParams.set('playlist_id', process.env.SL_PLAYLIST_ID);
  url.searchParams.set('pagesize', String(pageSize));
  url.searchParams.set('page', String(offset));   // an offset, not a page number
  url.searchParams.set('orderby', 'position');
  url.searchParams.set('encoded', '1');           // skip medias still encoding
  url.searchParams.set('f', 'json');

  // small dismissal lists can be pushed down to the platform
  const dismissed = await store.dismissedIds(user.id);
  if (dismissed.length && dismissed.length <= 30) {
    dismissed.forEach((id) => url.searchParams.append('not_media_ids[]', id));
  }

  const response = await fetch(url);
  if (!response.ok) throw new Error(`ws/playlist ${response.status}`);   // 404 = HTML error page

  const { playlist } = await response.json();
  const items = (playlist.medias ?? [])                                  // absent when nothing matched
    .map(({ media }) => media)
    .filter((m) => !dismissed.includes(m.metadata.global.media_id))      // large lists: filter here
    .filter((m) => !m.metadata.global.is_tokenized || m.metadata.global.has_password)
    .map((m) => ({
      id: m.metadata.global.media_id,
      title: m.metadata.global.name,                                     // absent on an untitled media
      duration: m.metadata.global.duration,
      ratio: m.metadata.global.ratio,                                    // absent while not encoded
      cover: m.metadata.customization?.cover?.thumbnaillarge_url,        // absent without a cover
      liked: false,   // filled from your own store
    }));

  res.json({ items, total: playlist.metadata.size, nextOffset: offset + pageSize });
});
```

Four details that bite:

- **`page` is an offset.** Advance it by `pagesize`, not by one,
- **check the status.** An unknown parameter value, an unknown playlist or a missing IP
  authorization all answer `404` with an HTML page, not a JSON error,
- **an empty value is an absent key.** Note the `??` and the `?.` above: a search that matched
  nothing has no `medias` key at all — read `metadata.size`, which is always there — and a media
  with no cover has no `customization.cover` object to reach into. A feed built on a curated
  playlist works for months, then crashes on the first media somebody published without a poster.
  Give every card a placeholder rather than trusting the block,
- **`not_media_ids[]` lives in the URL**, and the service is GET-only. Past a few dozen ids, filter
  in your backend and ask for a slightly larger page to compensate.

## 2. Play each card

**WebView, the short path.** One iframe per card:

```
https://cdn.streamlike.com/play?med_id=MEDIA_ID
  &pid=PLAYER_CONFIG_ID      // colours, logo, controls — set once in the back office
  &autostart=1&muted=1       // the only autoplay browsers allow
  &events=1                  // lets your page drive it
  &user_token=USER_TOKEN     // ties playback to this viewer
  &fill_browser=1            // fills the card, cropping rather than distorting
```

Everything is reported for you: playbacks, engagement, resume points. Drive the visible card with
`postMessage(['play'])` / `['pause']`, and listen for `["sl-state","ended"]` to advance — see
`references/player-embed.md`.

Pause the cards that scroll off screen. A dozen iframes all playing will saturate the device and
the connection, and will count as a dozen playbacks.

**Native player, the long path.** `ExoPlayer` or `AVPlayer` on the HLS master, which
`references/playback.md` explains how to find. Better control of gestures and preloading, at a
price: you must report playbacks (`o.k`) and engagement (`eng.k`) yourself, or the account's
statistics will show an empty app — see `references/analytics.md`. Handle protected medias
yourself too.

For a first version, the WebView path is usually right. Move to native when a measured problem
forces it.

## 3. Like

```js
app.post('/medias/:id/like', async (req, res) => {
  const user = await authenticate(req);
  await store.like(user.id, req.params.id);          // your truth

  // optional: contribute to the platform-wide rating
  const url = new URL('https://cdn.streamlike.com/ws/vote');
  url.searchParams.set('company_id', process.env.SL_COMPANY_ID);
  url.searchParams.set('media_id', req.params.id);
  url.searchParams.set('value', '5');
  await fetch(url);   // from a whitelisted server IP

  res.status(204).end();
});
```

`vote` requires a whitelisted server IP that cannot be waived, and the platform leaves
deduplication to you — check your own store before calling, or one enthusiastic user will move the
average on their own. The aggregate comes back in `/ws/media` as `statistics.rating_hits` and
`rating_totalvalue`.

Two things about the answer. **The accepted range is 0 to 5** from webservices 5.26, `0` being the
worst grade — so a "dislike" sent as `0` is stored, where an older server rejected it. And
rejection is quiet: the body is `{"vote":{"res":false}}` with a **200**, which covers both an
out-of-range value and a write that failed on our side. Read `res` before you tell the user
anything.

If a like is only ever a personal signal, skip `vote` entirely.

## 4. Dismiss

Store it, then apply it on the next fetch, as in step 1. Two variants worth knowing:

- **soft dismissal** — hidden for this user. Your store, filtered per request,
- **hard removal** — gone for everyone: remove the media from the playlist through the API
  (`POST /medias/{media_ids}/actions/organization/playlist`) or unpublish it
  (`PATCH /medias/{media_id}` with `visibility.state: offline`). Editorial action, not a per-user
  one, and it needs an API key on your backend.

Do not confuse the two. A per-user dismissal that reaches the API changes the catalog for everybody.

## 5. Resume, and continuity between sessions

Pass a stable `user_token` per account everywhere (player URL, `eng.k` as `u`), then read the last
position back:

```
https://cdn.streamlike.com/ws/resume?media_id=MEDIA_ID&user_token=USER_TOKEN
```

Use it to open a card where the viewer left it, or to skip what they already finished. The token is
pseudonymous data about a person: use an internal id, never an email.

Read what it gives you carefully. `timecode` is **always present** and `0` means three different
things — the token was never seen, the last view is more than a month old, or the viewer really is
at the start. And the value is **the furthest second reached during the last session**, not where
playback stopped: someone who jumped to the end and came back resumes at the end. In a swipe feed
that is an unpleasant surprise, so offer "resume" as a choice rather than seeking on open.

## 6. Prefetch without wasting data

- fetch the next page when the viewer is two or three cards from the end — the same rule the JS
  SDK's playlist player applies,
- preload covers (`customization.cover.thumbnaillarge_url`), not videos,
- on mobile data, cap the renditions with `max_height=720` (or `inline_throttling` on the Theo
  player) rather than letting a phone pull a 1080p ladder in a feed,
- `metadata.size` is the size of the whole playlist: use it for the end-of-feed state instead of
  probing for an empty page.

## Checklist before shipping

- [ ] The `company_id` and the API key exist only on the backend,
- [ ] every webservice call checks the HTTP status before parsing,
- [ ] every field read off a media is guarded — an empty value is an absent key, covers included,
- [ ] the feed advances by `pagesize`, and stops on `metadata.size`,
- [ ] off-screen players are paused,
- [ ] restricted medias are filtered or handled (`is_tokenized`, `has_password`, `is_secured`),
- [ ] if you play natively, `o.k` and `eng.k` are wired, and the figures in the console match a
      manual test,
- [ ] the `user_token` is stable per account and carries no personal data,
- [ ] likes and dismissals survive a reinstall, because they live server side.
