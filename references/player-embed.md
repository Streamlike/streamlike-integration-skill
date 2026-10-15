# The player: embedding and controlling it

The player is a hosted page you embed in an iframe. It handles adaptive streaming, subtitles,
chapters, interactions, multiple audio tracks, accessibility and playback reporting — none of which
you have to rewrite.

## Player URLs

```
https://cdn.streamlike.com/play?med_id=MEDIA_ID
https://cdn.streamlike.com/play?permalink=PERMALINK
https://cdn.streamlike.com/play?live_id=STREAM_NAME
https://cdn.streamlike.com/play?str_id=STREAMOUT_ID
```

`med_id` carries the same value as the `media_id` returned by the webservices. Options are added as
query parameters:

```
https://cdn.streamlike.com/play?med_id=MEDIA_ID&autostart=1&muted=1&events=1&active_color=001547
```

A **player configuration** created in the back office bundles those options behind one identifier,
and `&pid=CONFIG_ID` applies it. Prefer it: settings then change without touching your code, and
one account-wide default applies when no `pid` is given.

## Responsive embedding

The iframe has no intrinsic size. Wrap it in a box whose `padding-top` matches the aspect ratio —
`100 / ratio` in percent, with `ratio` read from `metadata.global.ratio` of `/ws/media`:

```html
<div style="position:relative;overflow:hidden;padding-top:56.25%">
  <iframe src="https://cdn.streamlike.com/play?med_id=MEDIA_ID"
          style="position:absolute;top:0;left:0;width:100%;height:100%;border:0"
          allow="autoplay; fullscreen; picture-in-picture"
          allowfullscreen webkitallowfullscreen mozallowfullscreen></iframe>
</div>
```

16:9 is 56.25%, 2:1 is 50%, 21:9 is 42.85%. The `allow` attribute matters: without `fullscreen` the
fullscreen button does nothing, without `autoplay` any autostart, even muted, is refused by the browser.

`setResponsiveIframe()` from `js-streamlike-sdk` does this from a media id, and fetches the ratio
for you — see `references/js-sdk.md`.

### Sizing on phones and small players

The player sizes its own controls to the box it is shown in — the iframe, so the tiers below read
the iframe's size, not the page's. Every size of the chrome (bar buttons, icons, text, the central
play button) derives from one base:

| Situation | Base | What changes |
| --- | --- | --- |
| default | 12px | 36px bar buttons, central button up to 120px |
| touch screen (`pointer: coarse`) | 15px | 45px buttons, the 44px target Apple and Google ask for; 150px central button |
| iframe narrower than 480px | — | the volume slider (the device has its own keys), the time readout and picture-in-picture leave the bar |
| iframe narrower than 300px or shorter than 230px | 10px | 30px buttons |

The central button also follows the iframe: 40% of its short side, between 48px and the tier's maximum (74px in a 330×185 iframe, 120px from 300px high).

A custom skin (the `skin` parameter) sets the base with one custom property, and the whole player
follows on both engines: `.slplayer { --sl-ui-scale: 13px; }`. The player never declares the
property — it reads it with a fallback per tier — so a skin's value wins whatever the loading
order, without `!important`; a value set unconditionally applies everywhere, phones included, and
`@media` rules on the same property keep tiers of your own. On iPhone and iPad, THEOplayer adds its
own mobile layout (centred menus, slightly larger icons) on top of these tiers.

## Controlling the player from the page

Add `events=1` to the player URL, then talk to the iframe with `postMessage`. Give the iframe an
id:

```html
<iframe id="slplayer" src="https://cdn.streamlike.com/play?med_id=MEDIA_ID&events=1"></iframe>
<script>
  const player = document.getElementById('slplayer');
  player.contentWindow.postMessage('["play"]', '*');
  player.contentWindow.postMessage('["seek",30.4]', '*');
  player.contentWindow.postMessage('["speed",1.9]', '*');
</script>
```

| Command | Effect |
| --- | --- |
| `["play"]` / `["pause"]` | Start / pause playback |
| `["mute"]` / `["unmute"]` | Sound off / on |
| `["fullscreen"]` | Toggle fullscreen |
| `["seek",30.4]` | Jump to a position, in seconds |
| `["speed",1.3]` | Playback rate — below 1 slows down, above 1 speeds up |
| `["volume",0.5]` | Volume, 0 to 1 |

The player pushes back on the same channel. Each message is a JSON **string** — parse it — whose
last item is the media id. `sl-progress` comes roughly every 250 ms while playing; `sl-state`
comes at each transition:

```js
window.addEventListener('message', (evt) => {
  if (evt.source !== player.contentWindow) return; // only this iframe
  const [type, value, mediaId] = JSON.parse(evt.data);
  // ["sl-progress", 24.363924, "MEDIA_ID"]  – current position in seconds
  // ["sl-state", "play", "MEDIA_ID"]        – see the table below
  console.log(type, value, mediaId);
});
```

| `sl-state` value | When |
| --- | --- |
| `ready` | A source is loaded and can play |
| `play` / `pause` | Playback starts / pauses |
| `ended` | A recorded media reached its end |
| `live-pending` | The live has not started yet. A state, not a one-shot event: see below |
| `live-waiting` | The live was flowing and its segments stopped. The player shows the cover and waits |
| `live-resumed` | The segments are back. Followed by `play` when playback restarts on its own |
| `live-ended` | The live is over. Sent once by the player |

The live states, in detail:

- **`live-pending` repeats.** Before the live starts, the iframe shows a waiting room that
  reloads every `live_wait` seconds (15 by default), and every reload posts `live-pending`
  again. Treat it as "still not started", not as a new event. With `live_wait=0` there is no
  waiting room: the player loads at once and posts `live-pending` itself,
- **the waiting room posts only when `events=1` (or `true`) and the page sits inside an
  iframe.** If it is reached for a live already over, it posts `live-ended` instead — at each
  reload, like `live-pending`,
- **`live-waiting` is not a pause.** No `pause` is sent when the segments stop, and the `ready`
  of the reloads that probe the live behind the cover are not sent either, until the next
  `play`,
- **`live-resumed` is not final either.** If playback has not restarted 20 seconds after it, the
  player puts the cover back and posts `live-waiting` again, then `live-resumed` once the stream
  really flows. Treat `sl-state` as a current state, the last message wins, not as a series of
  one-off events,
- **`live-ended` is final.** It is never followed by `pause` nor `ended`: `ended` stays the end
  of a recorded media, the signal you chain on.

Three practical notes:

- check where a message comes from (`evt.source`, or `evt.origin`) before trusting it: your page
  will receive messages from other frames too,
- `sl-state` `ended` is how you detect the end of a media to chain the next one; on a live, wait
  for `live-ended`,
- the iframe is cross-origin. You cannot read its DOM, and a click inside it sends keystrokes to
  the player, not to your page — keyboard shortcuts bound on your page stop working once the
  viewer has clicked the video.

## Keyboard shortcuts inside the player

| Key | Action |
| --- | --- |
| Space, `k` | Play / pause |
| `m` | Mute |
| `f` | Fullscreen |
| ← / → | ±5 seconds |
| ↑ / ↓ | Volume |
| `>` | Playback speed |
| `c` | Subtitles |
| `p` | Storyboard (mosaic) |
| `d` | Media information |
| `n` | Chapters |
| `0`–`9` | Jump to that tenth of the duration |

## oEmbed

The player is an oEmbed provider, which is what content management systems consume:

```
https://cdn.streamlike.com/oembed?url=<url-encoded player URL>&format=json
```

```json
{"version":"1.0","type":"video","provider_name":"Streamlike",
 "title":"…","thumbnail_url":"…","width":640,"height":358,
 "html":"<style>…</style><div class=\"sl-resp\"><iframe src=\"…\"></iframe></div>"}
```

The returned `html` is already responsive. `format=xml` is available too.

## Every player parameter

Values are read from the URL, or from the player configuration behind `pid` — the two are
equivalent, and a parameter in the URL overrides the configuration. Booleans are `0` or `1`.
Colours are hexadecimal without `#`. When a parameter accepts either a language code or a boolean,
`1` means "follow the browser language".

The last two columns say whether the parameter applies to a Streamlive (live channel) and to a
Streamout (scheduled broadcast).

| Parameter | Value | Description | Default | Streamlive | Streamout |
| --- | --- | --- | --- | --- | --- |
| `active_color` | RRGGBB | Changes the color of all the player's "active" elements (progress bar, active buttons, etc.). Takes an HTML color without the #. E.g. FF01F8 | - | yes | no |
| `audio_lng` | language code | Forces the audio track language. The -ad suffix targets the language's audio description: audio_lng=en-ad | - | no | no |
| `autostart` | bool | Automatic media start, with sound when the browser allows it, muted otherwise (see "Choosing parameters that matter") | 0 | yes | no |
| `background_audio` | bool | Switches to the lowest quality available if a video is playing but not visible | 0 | yes | yes |
| `background_color` | RRGGBB | Changes the background color behind the video and the poster. Takes an HTML color without the #. E.g. FF01F8 | - | yes | yes |
| `background_opacity` | integer | Only in combination with a background_color. Overrides the opacity setting of the background color. 0: transparent, 100: opaque | 100 | yes | no |
| `buttons_color` | RRGGBB | Changes the color of the overlaid buttons. Takes an HTML color without the #. E.g. FF01F8 | FFFFFF | yes | no |
| `chapter` | language code / bool | Forces the language or disables the display of chapters. E.g. chapter=fr or chapter=0 | 1 | no | no |
| `chapters_usethumb` | bool | Shows or disables the thumbnail | 1 | no | no |
| `controls` | bool | Whether to show the player controls | 1 | yes | no |
| `cover` | url / bool | URL of the image to use for the cover, or a boolean to enable/disable it | 1 | yes | no |
| `download` | bool / integer | displays a button to download the highest-quality transcode / displays a download button and caps the maximum bitrate of the file that can be downloaded | 0 | no | no |
| `events` | bool | Enables or disables the ability to control the player from outside the iframe | 0 | yes | no |
| `fill_browser` | bool | Enables or disables the playback mode that fills the entire browser window. In this mode, parts of the video may become hidden but it is not distorted. | 0 | yes | yes |
| `forcehd` | bool | Selects only the highest-quality stream (MP4 only) | 0 | no | no |
| `fs` | bool | Enables or disables switching to fullscreen | 1 | yes | yes |
| `fullscreen` | bool | Enables or disables switching to fullscreen | 1 | yes | yes |
| `icons_position` | right left none | Places the panel icons on the right or left, or fully disables the display of panels and icons | right | yes | no |
| `infos` | bool | Shows the title/description/credits block. Setting "nometa" to 1 disables this option | 0 | yes | no |
| `inline_throttling` | integer | Limits the quality of videos available in standard playback but not in fullscreen, by specifying a maximum bitrate (in Kbps). Both engines honour it | - | yes | yes |
| `interaction` | language code / bool | Forces the language or disables the display of interactions. E.g. interaction=fr or interaction=0 | 1 | no | no |
| `interface` | bool | Disables all interface elements (buttons, controls, panel, etc.) | 1 | yes | no |
| `landing` | bool | Shows the clickable cover image and a logo in place of the player. The player is loaded after clicking the image. | 0 | no | no |
| `live_dvr` | bool | Accepted for compatibility; the current player does not read it. The rewind window comes from the live itself: about 45 minutes when it was created with live[dvr]=true, about 100 seconds otherwise (API default: false since API 5.30) | 1 | yes | no |
| `live_id` | string | Identifier of the live or "stream name" | - | yes | no |
| `live_wait` | integer | Seconds between two reloads of the waiting room shown before a live starts. 0: no waiting room, the player loads at once and waits for the stream itself | 15 | yes | no |
| `logo` | bool | Whether to show the logo | 1 | yes | yes |
| `logo_alpha` | 0-100 | Overrides the transparency setting, only if the logo is defined from a logo_url parameter | 100 | yes | yes |
| `logo_id` | integer | applies the logo referenced by the ID | - | yes | yes |
| `logo_link` | url | Makes the logo clickable and opens the given url in a new window | - | yes | yes |
| `logo_position` | lb lt rt rb | Overrides the position setting (r: right, t: top, b: bottom, l: left), only if the logo is defined from a logo_url parameter | rt | yes | yes |
| `logo_url` | url | Overrides the URL of the logo image | - | yes | yes |
| `loop` | bool | Loops the media | 0 | no | no |
| `max_height` | integer | Sets a height limit for the transcodes made available for adaptive streaming. Combined with inline_throttling, the strictest rule prevails | - | yes | yes |
| `max_width` | integer | Sets a width limit on the transcodes made available for adaptive streaming. Combined with inline_throttling, the strictest rule prevails | - | yes | yes |
| `med_id` | string | encrypted media_id | - | no | no |
| `mosaic` | bool | Shows or disables the mosaic | 1 | no | no |
| `muted` | bool | Starts the media muted. With `autostart=1`, guarantees a silent start instead of the sound attempt | 0 | yes | yes |
| `nometa` | bool | No meta tag in the head (title, descriptions, keywords, og, etc.) | 0 | yes | yes |
| `nosharemeta` | bool | Disables the social sharing meta tags (included in nometa) | 0 | yes | yes |
| `nowplaying` | bool | Adds a clickable button to show the number of ongoing playbacks | 0 | yes | no |
| `permalink` | string | Permalink | - | no | no |
| `pid` | encrypted pid | Encrypted ID of the player settings to apply to the media | company default | yes | yes |
| `play_button` | bool | Shows or hides the central "play" button. | 1 | yes | no |
| `playback_speed` | bool | Shows the button to change the media playback speed | 0 | no | no |
| `player` | theo, hlsjs | Forces the playback engine. Ignored in three cases, where only one engine can do the job: a live always plays on `theo` (a streamout whose schedule holds a live too), `background_audio=1` always plays on `hlsjs`, and a quality-capped media (`throttling`, `inline_throttling`, `max_width`, `max_height`) always plays on `hlsjs` in Safari for macOS. Without this parameter, Safari (macOS, iOS, iPadOS) gets `theo` and other browsers get the player settings' value, `hlsjs` by default. `videojs` is accepted as an alias of `hlsjs` | hlsjs | yes | yes |
| `preload` | bool | Preloads the media | 0 | no | no |
| `prevent_click` | bool | Blocks clicking on the player | 0 | yes | no |
| `related` | bool or view_id | Shows a grid of media that share keywords and belong to the same view | 0 | no | no |
| `report` | bool | Shows the button to report inappropriate content | 0 | yes | no |
| `share` | bool | Whether to show the sharing block | 0 | yes | no |
| `skin` | id | Plain-text ID of the skin to use | - | yes | no |
| `slider` | bool | Shows or disables the slider | 1 | no | no |
| `sltoken` | string(32) | When token-based security is enabled, must contain the access token created by the API | - | yes | yes |
| `sltoken_duration` | integer | Token validity duration, in seconds | - | yes | yes |
| `sltoken_ip_ids` | string(32) | List of the IDs of the authorized IP groups, separated by commas | - | yes | yes |
| `sltoken_referrer_ids` | string(32) | List of authorized referrer identifiers, separated by commas | - | yes | yes |
| `str_id` | encrypted streamout id | encrypted streamout id | - | no | yes |
| `streamlike_mp_starttc` | integer | Position (in seconds) where the video should start | 0 | no | no |
| `subtitle` | language code / bool | Forces the language or disables the display of subtitles. The -cc suffix targets the language's closed captions. E.g. subtitle=fr, subtitle=fr-cc or subtitle=0 | 1 | no | yes |
| `subtitle_deep_links` | language code / bool | Forces the language or disables the display of subtitle search. E.g. subtitle_deep_links=fr or subtitle_deep_links=0 | 1 | no | yes |
| `subtitles_size` | integer | Font height in em | - | no | yes |
| `swfskin` | id | Plain-text ID of the skin to use | - | no | no |
| `t` | string | Position where the video should start. Accepted formats: hh:mm:ss.000 or shorter | 0 | no | no |
| `tc` | string | Position where the video should start. Accepted formats: hh:mm:ss.000 or shorter | 0 | no | no |
| `throttling` | integer | Limit the quality of available videos by specifying a maximum bitrate (in Kbps); sets a minimum quality threshold if the value is negative | - | yes | yes |
| `timecode` | string | Position where the video should start. Accepted formats: hh:mm:ss.000 or shorter | 0 | no | no |
| `tv` | bool | Removes the controls and the play button and forces automatic playback. Interactions stay visible but are not clickable. Default and non-editable setting for a streamout | 0 | yes | no |
| `user_token` | string(64) | Identifies a specific user by permanently assigning them the same token | - | yes | yes |
| `utm_source` | string | Your own label for where the traffic comes from (a newsletter, a campaign, a partner site), e.g. utm_source=newsletter-october. Reported with the playback and shown in the referrer statistics instead of the referring page, which browsers usually cut down to its origin. Free text, trimmed, first 100 characters kept | - | yes | yes |
| `volume` | float | Volume setting from 0.0 to 1.0 | 1.0 | yes | yes |
| `waveform` | bool | Audio media: shows the interactive waveform skin drawn from the media's sound. `0` restores the cover display, `1` forces the skin on a media that carries an uploaded cover. No effect when the media has no peaks file (see below) | 1 | no | no |
| `waveform_color` | RRGGBB | Accent color of the waveform; the background shade is derived from it. Takes an HTML color without the #. E.g. FF01F8 | 44B0A7 | no | no |

## Choosing parameters that matter

- **Autoplay**: `autostart=1` tries to start with sound, and falls back to a muted start when the
  browser refuses — no prior interaction with your site, a low engagement score. Whether sound is
  allowed is the browser's call, not yours; the fallback keeps the picture moving either way. Add
  `muted=1` when you want a silent start whatever the browser would have allowed: a feed of cards,
  a screen wall, a preview. The `<iframe>` needs `allow="autoplay"` in both cases,
- **Bandwidth**: `max_width` / `max_height` cap the renditions offered, `inline_throttling` caps
  the bitrate outside fullscreen, and the strictest rule wins, on both engines. Useful on mobile
  data or a constrained corporate network. In Safari for macOS a capped media is served by `hlsjs`
  whatever `player` says: that is the only engine able to honour a cap there,
- **`background_audio=1`** drops to the lowest quality when the video is playing but not visible.
  It is meant for audio-first usage, not for saving bandwidth on a visible player. It always runs
  on `hlsjs`, whatever `player` says,
- **Chrome**: `interface=0` removes every control for a decorative background video;
  `controls=0`, `play_button=0`, `logo=0`, `icons_position=none` remove pieces one by one,
- **Accessibility**: `audio_lng=en` forces an audio track, `audio_lng=en-ad` its audio
  description, `chapter=fr` and `interaction=fr` force those languages,
- **`user_token`** ties playback events to one viewer, which is what makes resume and per-viewer
  engagement possible — see `references/analytics.md`,
- **`tv=1`** strips the controls and forces playback, the signage mode.

## The waveform skin on audio media

An audio media whose encoding produced a peaks file plays under a SoundCloud-like waveform instead
of its cover: the wave draws the sound, a click or a drag on it seeks. Nothing to enable — the
skin is on by default whenever the peaks exist and the media has no cover of your own.

- **an audio media carrying a cover you uploaded shows that cover, not the skin.** The waveform
  covers the audios without one. To get the skin anyway on such a media, set its `waveform` field
  to `true` through the API, or pass `waveform=1` in the URL,
- `waveform=0` restores the cover display for one embed. The account-wide default is the
  `waveform` company preference, and a media can be forced either way through the API; the URL
  parameter always wins (`references/api.md`),
- `waveform_color=RRGGBB` sets the accent; the darker background shade is derived from it. Left
  unset, the account's `waveform_color` preference applies, then the platform teal (`44B0A7`),
- a custom skin (the `skin` parameter) can restyle it through two CSS custom properties,
  `--sl-waveform-color` and `--sl-waveform-background` — the skin stylesheet loads after the
  player's own colors, so a `:root` rule is enough,
- an audio media encoded before the feature has no peaks file: the skin stays off and the player
  renders as before. Re-encoding the media produces one,
- keyboard and assistive-tech users keep the classic seek bar: the waveform is a pointer-only
  companion surface, it removes nothing.

The peaks data itself is public and consumable outside the player — format and URLs in
`references/playback.md`.

## Legacy helper scripts

Older integrations load `sl5-utils.js` from `assets.streamlike.tv` and call
`new Streamlike().setResponsiveIframe(...)`. That path still works and still appears in the
platform documentation, but new work should use `js-streamlike-sdk`, which is typed, dependency
free and maintained.
