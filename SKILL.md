---
name: streamlike-integration
description: Build an integration on top of Streamlike — a web app, a mobile app, a WebTV, a portal, a back-office automation or a server-side ingest pipeline. Use whenever the work involves Streamlike medias, playlists, the Streamlike player (embed, iframe, postMessage), the Streamlike webservices (/ws/*), the Streamlike REST API (api.streamlike.com), the js-streamlike-sdk, or Streamlike playback URLs (cdn.streamlike.com/play). Covers picking the right door, authentication, catalog reading, playback, security, analytics and feeds.
---

# Integrating with Streamlike

Streamlike is a video platform: medias are uploaded, encoded, organized in playlists and played
through a hosted player. Three public surfaces are open to an integration, and picking the wrong
one is the single most expensive mistake in a Streamlike project.

## Pick the door before writing code

| You need to… | Use | Where it runs |
| --- | --- | --- |
| Show videos, playlists, covers, transcripts on a page or in an app | **Webservices** (`/ws/*`) + the **player iframe** | Server or client |
| Ship a web front fast, with a ready-made playlist player, thumbnails, transcripts | **`js-streamlike-sdk`** | Browser |
| Create, edit, delete medias; upload files; manage users, playlists, security, live | **REST API** | **Server only** |
| Read audience and engagement figures | **REST API** `/analytics/*`, or `/ws/media` for basic counters | Server |
| Publish a feed (RSS, podcast, Google video sitemap) | **Webservices** | Server |

Two rules that follow from that table, and that no integration may break:

- **the REST API never runs in a browser, a mobile app or anything the end user controls.** An API
  key carries the full rights of the user who created it: reading it out of a bundle means handing
  over the account. Front ends talk to your own backend; your backend talks to the API,
- **the webservices are the read path.** They are cache-friendly and fast; the API is not built for
  per-page-view reads and heavy front-end use of it may get the account throttled.

## What the client must obtain from Streamlike first

An integration cannot be started from nothing — these come from the Streamlike account manager or
the back office at `https://bo.streamlike.com`:

- a **company account**, created by Mediatech/Streamlike (there is no self-service signup and
  no shared demo account),
- the **`company_id`**, the account identifier used by most webservices,
- **API access enabled** on the account, then a **permanent API key** created in the back office
  (avatar menu → API keys). The key is shown once,
- for the webservices that require it (`vote`, `manifest`), the **public IP of your server**
  whitelisted in the back office, Security → Webservices security,
- optionally a **player configuration** (`pid`) so playback settings live in the platform instead
  of in your URLs.

## Identifiers you will meet

| Identifier | Looks like | Used by |
| --- | --- | --- |
| `media_id` | `3f9a1c07be24d5e1` | `/ws/media`, API `/medias/{media_id}`, player `med_id=` |
| `permalink` | `spring-product-launch` | `/ws/media?permalink=`, player `permalink=` |
| `playlist_id` | `b17c40de92f5a3c8` | `/ws/playlist`, API `/organization/playlists/{id}` |
| `view_id` | same shape | A saved subset of playlists, usable in place of `playlist_id` |
| `company_id` | same shape | Every webservice. Treat as a secret: it addresses the whole catalog |
| `pid` | same shape | Player configuration applied with `&pid=` |
| `user_token` | your own string, up to 64 chars | Ties playback events and resume points to one viewer |

`media_id` and the player's `med_id` carry the same value — the player parameter is simply named
differently for historical reasons.

## Thirty-second start

Play a media in a page, responsively:

```html
<div style="position:relative;overflow:hidden;padding-top:56.25%">
  <iframe src="https://cdn.streamlike.com/play?med_id=MEDIA_ID"
          style="position:absolute;top:0;left:0;width:100%;height:100%;border:0"
          allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe>
</div>
```

Read a catalog page, server side:

```bash
curl "https://cdn.streamlike.com/ws/playlist?playlist_id=PLAYLIST_ID&pagesize=10&f=json"
```

Everything else — options, filters, security, analytics — is in the references below.

## References

Read the one that matches the task; they are self-contained. Every path in this skill — here and
inside the reference files — is given from the root of the skill folder.

| File | Contents |
| --- | --- |
| `references/webservices.md` | The 15 `/ws/*` endpoints, parameters, response shapes and absence rules, paging, XML, error behaviour |
| `references/api.md` | REST API: authentication, conventions, `fields`/`range`/`sorts`, errors, responses that surprise, multipart, audio tracks, encoding version, endpoint map |
| `references/player-embed.md` | Player URLs, the full parameter table, `postMessage` control, keyboard shortcuts, oEmbed |
| `references/js-sdk.md` | `js-streamlike-sdk`: install, functions, playlist player, when it is the right tool |
| `references/playback.md` | HLS/CMAF delivery, multiple audio tracks, subtitles, waveform peaks, native players, offline pitfalls |
| `references/security.md` | Token-protected medias, IP/referrer restrictions, passwords, domains to whitelist |
| `references/analytics.md` | Playback counting, engagement, `user_token`, resume, ratings, reading the API reports |
| `references/feeds.md` | mRSS, podcast, Google video sitemap, QR codes, SCORM, short URLs |

Working calls against Streamlike's public demonstration catalog — copy, run, compare with what your
own code gets: `examples.md`.

Recipes, end to end:

| File | Scenario |
| --- | --- |
| `cookbook/mobile-feed-app.md` | A phone app scrolling through a playlist, liking and dismissing medias |
| `cookbook/webtv.md` | A catalog site: playlists, search, media pages, SEO |
| `cookbook/server-ingest.md` | Uploading and publishing medias from a backend |

## Tooling

The OpenAPI descriptions are public and authoritative:

- REST API — `https://api.streamlike.com/openapi.json` (~2.5 MB, 160+ paths),
- Webservices — `https://cdn.streamlike.com/openapi.json` (~90 KB).

The API file is far too large to read whole. Use the bundled tools instead:

```bash
scripts/fetch-openapi.sh                                # both files into scripts/openapi/
scripts/openapi_lookup.py tags                          # sections and how many paths each holds
scripts/openapi_lookup.py list --tag Medias             # one section
scripts/openapi_lookup.py search "audio track"          # full text over paths, summaries, parameters
scripts/openapi_lookup.py show /medias --method post    # parameters, body fields, responses
scripts/openapi_lookup.py fields /medias/{media_id}     # every field of the response
scripts/openapi_lookup.py --ws show /ws/playlist        # same, on the webservices description
```

The lookup downloads what it needs on first use, so it works from a clean checkout. Check the live
file before telling someone an endpoint exists: the published description trails the platform by a
release or two, and it is what their account actually answers to. The per-endpoint list of
validation error codes is not in the file — it is in the interactive documentation of the back
office.

## Working rules for this skill

- **Never invent an endpoint, a parameter or a field name.** Look it up with
  `scripts/openapi_lookup.py`, or in the reference files here, or fetch the media once and read the
  JSON. The webservices answer `404` with an HTML error page for an unknown parameter value, so a
  typo does not announce itself,
- **an empty value is an absent key, on both surfaces.** Neither the API nor the webservices send
  `null` or `0` to say "nothing here" — the key is simply gone, and a container left empty goes with
  it. So read defensively everywhere: guard before walking into an object, test presence before
  comparing a value, and never write a branch that only fires on `null`. The handful of endpoints
  that break the rule and *do* send nulls are called out where they appear,
- prefer `permalink` over `media_id` in URLs the end user sees, and `pid` over long parameter
  strings in embed URLs,
- when the integration is a public front end, assume the catalog is not entirely playable: some
  medias are token-protected or restricted by IP or referrer. `references/security.md` explains how
  to detect them instead of showing a broken player,
- the platform ships SDKs — `js-streamlike-sdk` (TypeScript, npm and CDN), `php-api-sdk` and
  `php-ws-sdk` on `https://github.com/Streamlike`. Reach for them before writing HTTP plumbing,
- Streamlike publishes technical articles for developers at `https://www.streamlike.fr/blog/` —
  worked examples, new features and integration notes that go beyond this reference. Worth a look
  when a subject here is thinner than your problem.
