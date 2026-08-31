# Feeds, sharing and packaging

Ready-made outputs that save writing a generator.

## WebTV profiles: where the links point

Feeds contain links, and the platform has to know what a link to one of your medias looks like. A
**WebTV profile** holds two base URLs — one for a media, one for a playlist:

```
media URL:    https://www.example.com/media.php?permalink=
playlist URL: https://www.example.com/playlist.php?playlist_id=
```

Create it in the back office (Rendering → WebTV profiles) or through `/profiles` in the API, then
pass `profile_id=` to a feed. A profile marked as default applies with no parameter. Without a
profile, links point at the Streamlike player.

## mRSS

```
https://cdn.streamlike.com/ws/rss?playlist_id=PLAYLIST_ID&profile_id=PROFILE_ID
```

An mRSS 2.0 feed of a playlist or a company, filtered like `/ws/playlist` (`company_id`,
`playlist_id`, `lng`, `query`, `orderby`, `sortorder`, `page`, `pagesize`). Only online medias are
included. Specification: `http://www.rssboard.org/media-rss`. A `playlist_id` always wins over a
`query`: the search term is read only when no playlist is given.

Three things in the items are not what a feed reader assumes:

- **`<enclosure length="…">` is the duration in seconds**, where the RSS specification asks for the
  size of the file in bytes. And its `url` is the same page URL as `<link>` — a web page, not a
  media file — while its `type` describes the media (`audio/mpeg` or `video/mp4`), not what that
  URL actually serves. A downloader that trusts the enclosure fetches an HTML page and files it as
  a 265-byte MP4,
- **`<description>` is not the description you typed.** When the media has a cover, an `<img>` tag
  pointing at its thumbnail is prepended to the text. A media with a cover and no description
  therefore has a `<description>` holding nothing but that tag. Strip the leading tag if you want
  the prose,
- **`CDATA` comes and goes.** Item text is wrapped in `CDATA` only when it contains `&`, `<` or
  `>`, so the same media gives `<title>Mediatech Audio</title>` one day and
  `<title><![CDATA[Mediatech & Audio]]></title>` the next, purely because someone added an
  ampersand. **Parse with an XML parser**, never by matching strings.

Without a `playlist_id` — that is, when you search — the channel `<title>` is the literal string
`Search result` rather than your search term, and there is no `<link>` at all.

## Podcast

```
https://cdn.streamlike.com/ws/podcast?playlist_id=PLAYLIST_ID&lng=fr&orderby=releasedate
```

A podcast feed built from a playlist of audio or video medias, provided the HTML5 option is enabled
on the account. Only `playlist_id`, `lng` and `orderby` apply. Per-playlist podcast metadata (name,
author, category, cover) comes from the platform and is returned by `/ws/playlists`.

**Two guards decide whether there is a body at all**, and both are settings in the back office
rather than parameters here: a playlist whose podcast has no category answers **404**, and a
playlist with no description, or a podcast with no link, answers **400**. Fill those in before
wiring a directory to the feed.

Unlike `rss`, `<link>` and `<enclosure url>` here point at the **file** — `/m/pod/{media_id}.mp4`
or `/m/mp3/{media_id}.mp3` — and `<description>` is the raw description, with no image prepended.
`<enclosure length="…">` is again the **duration in seconds**, not a size, and `<itunes:duration>`
is a plain number of seconds (`265`), never `hh:mm:ss`.

One reversal to keep in mind: inside an item, **an empty value gives an empty element, not a
missing one**. A media with no credits still carries `<author/>`, one with no keywords still
carries `<itunes:keywords/>`. That is the opposite of the JSON services, where an empty value means
the key is gone — test the content, not the presence.

## Google video sitemap

```
https://cdn.streamlike.com/ws/videositemap?playlist_id=ID1|ID2|ID3&profile_id=PROFILE_ID
```

Generates the sitemap search engines expect: for each media a `<loc>` built from the profile, plus
title, description, large thumbnail, file URL, player URL, duration, publication date and keywords.
Several playlists are joined with `|`; `company_id` covers the whole account. `no_content_loc`
leaves out the direct file URL when you do not want it exposed. Audio medias are listed too, in a
`<video:video>` like the rest, with an MP3 in `<video:content_loc>` — the name of the service says
video, the selection does not.

**Check the root element before you trust the status code.** When the account has no WebTV profile
and none was given, the body is not a sitemap: it is `<error>No profile exists</error>`, with no
XML declaration and no `<urlset>`, served with **HTTP 200** and the same content type. A crawler
that only looks at the status happily records an empty catalog.

```js
const doc = parse(response.body);
if (!doc.urlset) { throw new Error(doc.error ?? 'unexpected sitemap payload'); }
```

Two more edges, both of which produce entries Google rejects rather than entries it skips:

- **there is no fallback for `<loc>` here**, unlike `rss`. A profile with an empty media URL
  produces a `<loc>` that is nothing but an identifier. Configure the profile before publishing,
- **`<video:duration>` is always present and reads `0`** when the platform does not know the
  duration. It is not omitted. `<video:thumbnail_loc>` and `<video:description>`, on the other
  hand, are absent when the media has no cover and no description — and Google requires the
  thumbnail.

Regenerate it whenever you publish — a sitemap is only useful while it matches the site.

## QR codes

```
https://cdn.streamlike.com/ws/qr?media_id=MEDIA_ID&size=6&level=M
```

Despite the name, the service does not return the image: it answers an HTML `<img>` tag pointing at
a generated PNG on the CDN.

```html
<img src="https://cfcdn.streamlike.com/qr/2445c6da7e4a2744b3ac89b6fea0767d.png" alt=""/>
```

Parse out the `src` if you need the file itself. `size` sets the module size, `level` the error
correction level. Handy for print and signage.

**The `src` comes back as `https://` from webservices 5.26.** Before that it followed the scheme of
the short link the code encodes, which is built without TLS, so a fresh code came back as `http://`
and browsers blocked it as mixed content in a secure page. Against an older server, rewrite the
scheme yourself — the same file is served over both.

The PNG is stable and cacheable — its name is derived from the target URL, the level and the size,
and an existing short link is reused rather than minted again, so the same media, level and size
always give the same `src`, and **you can cache that URL** instead of calling again. What the code
encodes is the **standalone player page** (`/play?med_id=…`), not your WebTV and not the permalink
form, whatever the account's profile says.

## Short URLs

`GET /tools/shorturl` in the API turns a URL into a Streamlike short link and generates its QR
code. `Streamlink` endpoints (`/streamlink/urls`, `POST /streamlink/urls/media/{media_id}`) create
and manage short URLs bound to a media, when you need one that keeps working as the media changes.

## SCORM

```
GET /medias/{media_id}/scorm
```

Returns a SCORM 1.2 package (ZIP) wrapping the media in an iframe — the shape an LMS expects for
e-learning catalogs.

## Social platforms

The platform can push a media to linked YouTube and Dailymotion accounts:
`GET /medias/{media_id}/social` lists linkable accounts,
`POST /medias/{media_id}/social/{account_id}` links one,
`POST /medias/{media_id}/social/{account_id}/push` forces the push. Accounts themselves are managed
under `/social/accounts`.
