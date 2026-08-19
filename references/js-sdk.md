# `js-streamlike-sdk`

The official browser SDK: TypeScript, MIT, **no runtime dependency**. Current version 3.8.0.

```
https://github.com/Streamlike/js-streamlike-sdk
https://www.npmjs.com/package/js-streamlike-sdk
```

It wraps the webservices and the player, and ships ready-made UI pieces. When the target is a web
front end — including a WebView-based mobile app — start here rather than writing fetch calls.

## Install

```bash
npm install js-streamlike-sdk
```

Or straight from a CDN, no build step:

```html
<div id="my-player"></div>
<script type="module">
  import { generatePlaylistPlayer } from 'https://cdn.jsdelivr.net/npm/js-streamlike-sdk@3.8.0/dist/index.mjs';
  await generatePlaylistPlayer('my-player', { playlistId: 'PLAYLIST_ID' });
</script>
```

A classic script tag works too (`dist/index.global.js`, everything under the `Streamlike` global).
Pin an exact version: `@latest` changes behaviour under pages you no longer control. A CDN also adds
a third party to your pages — integrations that cannot accept that should install through npm and
serve the files themselves.

## What it gives you

**Data — thin wrappers over `/ws/*`:**

| Function | Endpoint |
| --- | --- |
| `getWsMedia(params, options)`, `getMediaFromId(id, …)`, `getMediaFromPermalink(permalink, …)` | `/ws/media` |
| `getMediaMetadata(…)`, `getMediaStatistics(…)` | `/ws/media`, narrowed |
| `getWsPlaylist(…)`, `getMediasFromPlaylist(id, …)`, `getMediasFromView(id, …)`, `getMediasFromCompany(id, …)`, `getPlaylistSize(…)` | `/ws/playlist` |
| `getWsPlaylists(…)`, `getPlaylists(…)` | `/ws/playlists` |
| `getWsRelated(…)`, `getWsNowPlaying(…)`, `getWsResume(…)`, `getWsCountries(…)`, `getWsLanguages(…)` | matching services |
| `getWs(url, debug)` | any endpoint URL |

**UI:**

| Function | What it renders |
| --- | --- |
| `setResponsiveIframe(mediaId, containerId, options)` | A responsive player, ratio fetched from the media |
| `embedPlayerIframe(container, src, ratio, params, debug)` | Same, from a player URL you built |
| `generateThumbnail(target, mediaCustomization, options)` | An interactive preview — `mode: 'animation'` or `'scrubbing'`, `fitMode` cover/contain |
| `generateWords(url, options)` | A live transcript, highlighted and clickable, synchronised with the player |
| `generateTrimmer(target, options)` | A segment selector bound to your inputs |
| `generatePlaylistPlayer(target, options)` | A complete playlist player |

## `setResponsiveIframe`

```js
import { setResponsiveIframe } from 'js-streamlike-sdk';

const response = await setResponsiveIframe('MEDIA_ID', 'player-container', {
  playerParams: { events: 1, autoplay: true, active_color: '293c5a' },
  baseOptions: { debug: true }
});

if (response.res) {
  console.log(response.data.metadata.global.name);
}
```

`playerParams` accepts every player parameter from `references/player-embed.md`. Note the return
shape: metadata lives under `response.data.metadata`, and `response.res` is the success flag.

## `generatePlaylistPlayer`

The one function that turns a playlist into a working interface: player, previous/next, clickable
list, information panel, auto-advance, paging, shareable timecoded links.

```js
const controller = await generatePlaylistPlayer('playlist-player', {
  playlistId: 'PLAYLIST_ID',
  info:     { title: true, position: true, duration: true, views: false, description: false },
  listItem: { thumbnail: true, index: true, title: true, duration: true },
  listPosition: 'right',      // 'right' | 'left' | 'bottom' | 'top'
  pageSize: 10,               // medias per request
  autoNext: true,
  hideTokenized: true,        // drop medias that cannot be played
  fullscreen: false,
  autostart: false,
  loop: false,
  labels: { previous: 'Previous', next: 'Next' },
  onMediaChange: (media, index) => {},
  onPlaylistEnd: () => {}
});
```

The controller exposes `play`, `pause`, `seek`, `next`, `previous`, `playIndex`, `playMedia`,
`loadMore`, `getCurrentIndex`, `getCurrentMedia`, `getMedias`, `getTotal`, `getCurrentTime`,
`isFullscreen`, `toggleFullscreen`, `getShareUrl`, `destroy`.

Behaviour worth knowing before you fight it:

- **paging is automatic.** Medias load `pageSize` at a time; nearing the end of the loaded set
  fetches the next page, a "load more" button appears while medias remain, and the counter reads
  `20 / 330`. `getTotal()` is the real size,
- **restricted medias are handled.** Token-protected medias are hidden by default and removed from
  the counts, so positions stay consistent; medias secured by IP or referrer keep their player and
  only show a notice if playback actually fails. The player probes the URL with a `HEAD` request
  rather than guessing,
- **`fullscreen: true` fullscreens the container**, not the iframe — which is what keeps playback
  running when the media changes. It disables the player's own fullscreen button, and steps aside
  on iPhone where Safari only fullscreens a native video element,
- **`shareParams: { enabled: true }`** reads `?media=…&t=…` from the page URL and
  `controller.getShareUrl()` builds such a link for the current position,
- **styling** is class-based, every element prefixed with `classPrefix` (`sl-playlist` by default),
  single-class selectors so your CSS wins. `injectStyles: false` starts from nothing,
- `listItem.interactiveThumbnail` downloads one storyboard per entry — fine for a few dozen items,
  not for hundreds.

## Transcript and trimmer

`generateWords(wordsUrl, { wordsContainer, iframePlayer, autoScroll })` needs the words file of a
subtitle track, found at `media.metadata.subtitles[0].subtitle.url.words`, plus the player iframe —
so call it after the player exists. `generateTrimmer` binds a start/end selector to your own number
inputs, for editing tools.

## When not to use it

The SDK is browser-side, so it only reaches what the webservices expose. Anything that writes —
creating medias, editing metadata, issuing playback tokens — goes through your backend and the REST
API. There is no JavaScript SDK for the REST API, and there should not be one in a browser.
