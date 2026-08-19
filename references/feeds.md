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
included. Specification: `http://www.rssboard.org/media-rss`.

## Podcast

```
https://cdn.streamlike.com/ws/podcast?playlist_id=PLAYLIST_ID&lng=fr&orderby=releasedate
```

A podcast feed built from a playlist of audio or video medias, provided the HTML5 option is enabled
on the account. Only `playlist_id`, `lng` and `orderby` apply. Per-playlist podcast metadata (name,
author, category, cover) comes from the platform and is returned by `/ws/playlists`.

## Google video sitemap

```
https://cdn.streamlike.com/ws/videositemap?playlist_id=ID1|ID2|ID3&profile_id=PROFILE_ID
```

Generates the sitemap search engines expect: for each media a `<loc>` built from the profile, plus
title, description, large thumbnail, file URL, player URL, duration, publication date and keywords.
Several playlists are joined with `|`; `company_id` covers the whole account. `no_content_loc`
leaves out the direct file URL when you do not want it exposed.

Regenerate it whenever you publish — a sitemap is only useful while it matches the site.

## QR codes

```
https://cdn.streamlike.com/ws/qr?media_id=MEDIA_ID&size=6&level=M
```

Despite the name, the service does not return the image: it answers an HTML `<img>` tag pointing at
a generated PNG on the CDN.

```html
<img src="http://cfcdn.streamlike.com/qr/2445c6da7e4a2744b3ac89b6fea0767d.png" alt=""/>
```

Parse out the `src` if you need the file itself; the PNG is stable and cacheable. `size` sets the
module size, `level` the error correction level. Handy for print and signage.

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
