# Working examples, on the public demo catalog

Every call below runs as-is, against Streamlike's own public demonstration catalog. Use them to see
the shape of a real response before wiring your own account, and to check that a problem comes from
your code rather than from the platform.

| What | Value |
| --- | --- |
| Media | `9dd61d7f5e077fdb` — "Streamlike motion design presentation", 75 s, 16:9 |
| Playlist | `7e0b55bbd4bd0a91` — "Films Streamlike", 51 medias |
| Multi-track media | `de342d715dbb4ce9` — two audio tracks, French and English subtitles |

These are public, unprotected medias. The demo account's `company_id` is deliberately not published
here: it addresses a whole catalog, and the services that need one work the same with yours.

## Read a media

```bash
curl -s "https://cdn.streamlike.com/ws/media?media_id=9dd61d7f5e077fdb" | jq .
curl -s "https://cdn.streamlike.com/ws/media?permalink=streamlike-motion-design-presentation-1770224042617" | jq .
```

```json
{"media": {"metadata": {"global": {
  "media_id": "9dd61d7f5e077fdb", "name": "Streamlike motion design presentation",
  "type": "video", "status": "online", "duration": 75, "ratio": 1.7777777777778,
  "is_tokenized": false, "is_secured": false, "has_password": false,
  "is_multiple_audio": false }}}}
```

Useful one-liners:

```bash
# title, duration and aspect ratio
curl -s "https://cdn.streamlike.com/ws/media?media_id=9dd61d7f5e077fdb" \
  | jq '.media.metadata.global | {name, duration, ratio}'

# every cover size
curl -s "https://cdn.streamlike.com/ws/media?media_id=9dd61d7f5e077fdb" \
  | jq '.media.metadata.customization.cover'
```

## Walk a playlist

```bash
# first page — remember: `page` is an offset
curl -s "https://cdn.streamlike.com/ws/playlist?playlist_id=7e0b55bbd4bd0a91&pagesize=5&page=0" \
  | jq '{size: .playlist.metadata.size,
         items: [.playlist.medias[].media.metadata.global | {media_id, name}]}'

# next page
curl -s "https://cdn.streamlike.com/ws/playlist?playlist_id=7e0b55bbd4bd0a91&pagesize=5&page=5" | jq .

# sorted by name, descending — `down`, not `desc`
curl -s "https://cdn.streamlike.com/ws/playlist?playlist_id=7e0b55bbd4bd0a91&pagesize=5&orderby=name&sortorder=down" | jq .

# search inside titles, descriptions and spoken words
curl -s "https://cdn.streamlike.com/ws/playlist?playlist_id=7e0b55bbd4bd0a91&query=live&search_fields%5B%5D=name&search_fields%5B%5D=transcription" | jq .

# two playlists at once — repeat the parameter
curl -s "https://cdn.streamlike.com/ws/playlist?playlist_id%5B%5D=7e0b55bbd4bd0a91&playlist_id%5B%5D=5236a84e5723dca3&pagesize=3" | jq '.playlist.metadata.size'
```

Exclude a media the way a "dismiss" feature would, and watch `size` drop by one:

```bash
curl -s "https://cdn.streamlike.com/ws/playlist?playlist_id=7e0b55bbd4bd0a91&pagesize=3&not_media_ids%5B%5D=9dd61d7f5e077fdb" \
  | jq '.playlist.metadata.size'
```

## See an error

The webservices answer `404` with an HTML page — never assume the body is JSON:

```bash
curl -s -o /dev/null -w "%{http_code} %{content_type}\n" \
  "https://cdn.streamlike.com/ws/playlist?playlist_id=7e0b55bbd4bd0a91&sortorder=desc"
# 404 text/html   ← `desc` is not a valid value; `down` is
```

## Related medias, live viewers

```bash
curl -s "https://cdn.streamlike.com/ws/related?media_id=9dd61d7f5e077fdb&pagesize=3" \
  | jq '[.medias[].media.metadata.global.name]'

curl -s "https://cdn.streamlike.com/ws/nowplaying?media_id=9dd61d7f5e077fdb" | jq .
```

`related` matches on keywords: it comes back empty on catalogs where nobody filled them in.

## A media with several audio tracks

```bash
curl -s "https://cdn.streamlike.com/ws/media?media_id=de342d715dbb4ce9" \
  | jq '{multi: .media.metadata.global.is_multiple_audio,
         subtitles: [.media.metadata.subtitles[].subtitle.language_id]}'
# {"multi": true, "subtitles": ["fr", "en"]}
```

The `multiple_audio` filter of `/ws/playlist` reaches the same result on a whole playlist, once
webservices 5.20 is deployed — today the parameter is accepted and ignored.


Force a track, or its audio description, in the player:

```
https://cdn.streamlike.com/play?med_id=de342d715dbb4ce9&audio_lng=en
https://cdn.streamlike.com/play?med_id=de342d715dbb4ce9&subtitle=fr
```

## Embed the player

```html
<div style="position:relative;overflow:hidden;padding-top:56.25%">
  <iframe src="https://cdn.streamlike.com/play?med_id=9dd61d7f5e077fdb&events=1"
          style="position:absolute;top:0;left:0;width:100%;height:100%;border:0"
          allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe>
</div>
```

Open it directly to try parameters:

```
https://cdn.streamlike.com/play?med_id=9dd61d7f5e077fdb
https://cdn.streamlike.com/play?permalink=streamlike-motion-design-presentation-1770224042617&autostart=1&muted=1
https://cdn.streamlike.com/play?med_id=9dd61d7f5e077fdb&interface=0&play_button=0
https://cdn.streamlike.com/play?med_id=9dd61d7f5e077fdb&active_color=cc0000&icons_position=left
```

## oEmbed

```bash
curl -s "https://cdn.streamlike.com/oembed?url=https%3A%2F%2Fcdn.streamlike.com%2Fplay%3Fmed_id%3D9dd61d7f5e077fdb&format=json" | jq .
```

Returns `title`, `thumbnail_url`, `width`, `height` and a ready-to-paste responsive `html` block.

## Reach the files

```bash
# let the platform pick the file for a target size (302 to the CDN)
curl -s -o /dev/null -w "%{redirect_url}\n" \
  "https://cdn.streamlike.com/html5/mp4/media_id/9dd61d7f5e077fdb/width/1280/height/720"

# the file manifest: every rendition, plus the adaptive master (globalbitrate 0)
curl -s "https://cdn.streamlike.com/ws/media?media_id=9dd61d7f5e077fdb" \
  | jq -r '.media.html5_sources[0].html5_source.manifest' | xargs curl -s | jq 'keys'
```

## Feeds

```bash
curl -s "https://cdn.streamlike.com/ws/rss?playlist_id=7e0b55bbd4bd0a91&pagesize=3"
curl -s "https://cdn.streamlike.com/ws/videositemap?playlist_id=7e0b55bbd4bd0a91" | head -40
curl -s "https://cdn.streamlike.com/ws/qr?media_id=9dd61d7f5e077fdb&size=6&level=M"
# <img src="http://cfcdn.streamlike.com/qr/….png" alt=""/>
```

## The JS SDK, end to end

Save as an `.html` file and open it — no build step, no account needed:

```html
<!doctype html>
<meta charset="utf-8">
<title>Streamlike SDK demo</title>
<div id="channel" style="max-width:960px;margin:2rem auto"></div>
<script type="module">
  import { generatePlaylistPlayer } from 'https://cdn.jsdelivr.net/npm/js-streamlike-sdk@3.8.0/dist/index.mjs';

  const controller = await generatePlaylistPlayer('channel', {
    playlistId: '7e0b55bbd4bd0a91',
    listPosition: 'right',
    pageSize: 10,
    autoNext: true,
    info: { title: true, position: true, duration: true },
    onMediaChange: (media, index) => console.log(index, media.metadata.global.name)
  });

  console.log('playlist size:', controller.getTotal());
</script>
```

## What you cannot try here

The REST API needs an account and a key, so nothing in `references/api.md` is exercised above.
`vote` and `manifest` need a whitelisted server IP. Ask Mediatech/Streamlike for an account, then repeat the
calls with your own identifiers — the shapes are the same.
