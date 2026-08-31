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
`customization.cover.thumbnaillarge_url`, `permalink`. Give the card a placeholder cover: a media
without a poster has no `customization.cover` object at all, and neither has one whose encoding is
still running. Paginate on `metadata.size`, which is always there — the `medias` key is not.

**A media page.** `/ws/media?permalink=…` — permalinks make readable URLs and survive re-encodings.
Add `related` for a "more like this" strip; it matches on keywords, so it is empty on catalogs
where nobody filled them in, and it never returns a live nor a media that is not encoded yet.

**Search.** `/ws/playlist?query=…&search_fields[]=name&search_fields[]=description&search_fields[]=keywords`.
Available fields: `id`, `name`, `description`, `credits`, `keywords`, `customs`, `transcription`,
`permalink`, `subtitle` — searching `transcription` and `subtitle` finds spoken words inside
videos, which is usually the feature people are impressed by. The matching excerpts come back in
`metadata.highlight` on the medias that matched, with the words wrapped in `<em>` — that is what
turns a result list into a useful one, and what lets you deep-link to a timecode when a subtitle
matched. **Stay in JSON when you search on a server older than webservices 5.26**: the excerpts
came out under element names XML does not allow, and the document you got back with `query` and
`f=xml` together did not parse at all. From 5.26 each excerpt sits in a `<value>` and XML works.

**Languages and countries.** `/ws/languages` and `/ws/countries` build filters that only offer
values the catalog actually has. Watch the case — `languages` answers `fr`, `countries` answers
`FR` — and note that both count encoded medias whatever their visibility, so they describe the
catalog rather than what a visitor can watch today.

## Caching

Server-side caching is not an optimisation here, it is the documented expectation: a page that
calls several services per view should render from your own cache, and the platform reserves the
right to restrict accounts that hammer the webservices. A short TTL (a minute or two) on playlist
and media responses is usually enough, with a purge when you publish.

## SEO

- **video sitemap**: `/ws/videositemap?playlist_id=…&profile_id=…`, regenerated when you publish.
  The WebTV profile is what makes the links point at your pages instead of the player —
  `references/feeds.md`. **Check that the root element is `<urlset>` before you ship the file**: a
  missing profile answers `<error>No profile exists</error>` with a `200`, and a pipeline that only
  looks at the status code publishes an empty sitemap,
- **oEmbed**: `https://cdn.streamlike.com/oembed?url=…&format=json` gives other sites a clean way to
  embed your medias,
- **mRSS and podcast feeds** for syndication and podcast directories,
- let the player emit its own metadata (leave `nometa` off) so shared links unfurl with a title and
  a thumbnail.

## Bandwidth and abuse

Public pages hand out embed codes whether you offer them or not. Referrer protection is what keeps
the traffic yours — `references/security.md`. Watch the referrers report in the console: playback
from domains you do not recognise is the visible symptom.
