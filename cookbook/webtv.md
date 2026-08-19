# A WebTV or video portal

A site whose pages are playlists and medias: browse, search, watch, and be found by search engines.

## The fast route

`generatePlaylistPlayer` from `js-streamlike-sdk` already is a WebTV page — player, list, paging,
information panel, shareable timecoded links, restricted medias handled:

```html
<div id="channel"></div>
<script type="module">
  import { generatePlaylistPlayer } from 'https://cdn.jsdelivr.net/npm/js-streamlike-sdk@3.8.0/dist/index.mjs';
  await generatePlaylistPlayer('channel', {
    playlistId: 'PLAYLIST_ID',
    listPosition: 'right',
    pageSize: 12,
    autoNext: true,
    shareParams: { enabled: true }
  });
</script>
```

Style it through the `sl-playlist-*` classes. Build the rest of the site around it — and only write
your own player when a real requirement outgrows the options in `references/js-sdk.md`.

## The structured route

**Channels.** `/ws/playlists?company_id=…` lists the online playlists. A **view** groups a subset
of playlists and can be used in place of a `playlist_id` in most services — the way to publish one
slice of the catalog to one site.

**A channel page.** `/ws/playlist?playlist_id=…&pagesize=12&page=0&orderby=position` returns the
medias with everything a card needs: `name`, `duration`, `ratio`,
`customization.cover.thumbnaillarge_url`, `permalink`.

**A media page.** `/ws/media?permalink=…` — permalinks make readable URLs and survive re-encodings.
Add `related` for a "more like this" strip; it matches on keywords, so it is empty on catalogs
where nobody filled them in.

**Search.** `/ws/playlist?query=…&search_fields[]=name&search_fields[]=description&search_fields[]=keywords`.
Available fields: `id`, `name`, `description`, `credits`, `keywords`, `customs`, `transcription`,
`permalink`, `subtitle` — searching `transcription` and `subtitle` finds spoken words inside
videos, which is usually the feature people are impressed by.

**Languages and countries.** `/ws/languages` and `/ws/countries` build filters that only offer
values the catalog actually has.

## Caching

Server-side caching is not an optimisation here, it is the documented expectation: a page that
calls several services per view should render from your own cache, and the platform reserves the
right to restrict accounts that hammer the webservices. A short TTL (a minute or two) on playlist
and media responses is usually enough, with a purge when you publish.

## SEO

- **video sitemap**: `/ws/videositemap?playlist_id=…&profile_id=…`, regenerated when you publish.
  The WebTV profile is what makes the links point at your pages instead of the player —
  `references/feeds.md`,
- **oEmbed**: `https://cdn.streamlike.com/oembed?url=…&format=json` gives other sites a clean way to
  embed your medias,
- **mRSS and podcast feeds** for syndication and podcast directories,
- let the player emit its own metadata (leave `nometa` off) so shared links unfurl with a title and
  a thumbnail.

## Bandwidth and abuse

Public pages hand out embed codes whether you offer them or not. Referrer protection is what keeps
the traffic yours — `references/security.md`. Watch the referrers report in the console: playback
from domains you do not recognise is the visible symptom.
