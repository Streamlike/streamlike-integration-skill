# Security

Two things are protected, and they have nothing to do with each other: **who may play a media**,
and **who may call the platform on your behalf**.

## Protecting playback

Four mechanisms, combinable, all configured per media in the back office or through the API:

| Mechanism | What it restricts | Weakness |
| --- | --- | --- |
| **Referrer** | Playback only from listed domains | Only meaningful when the Streamlike player is used |
| **IP range** | Playback only from listed addresses | Rules out mobile networks, whose ranges rotate |
| **Password** | The player asks for it before playing | Shareable, like any password |
| **Token** | One device, one IP, one time window | Requires a backend to issue tokens |

Token protection may be combined with referrer or IP-group protection: enable it with dynamic token
generation, then pass the authorized ids in the player URL.

Nothing here survives a viewer filming their screen. Referrer protection is nonetheless the
practical answer to bandwidth theft: without it, anyone can copy your embed code — or the direct
file URL if you built your own HTML5 player — and have the traffic billed to your account.

### Issuing a playback token

Server side, for a viewer you have just authenticated:

```bash
curl -X POST "https://api.streamlike.com/medias/MEDIA_ID/token" \
     -H 'X-Streamlike-Authorization: streamlikeAuth token="YOUR_KEY"' \
     -d "expire_at=2026-08-19T18:00:00Z" \
     -d "ip=VIEWER_IP" \
     -d "user_agent=VIEWER_USER_AGENT"
```

`201` returns the token with its `id`, `ip`, `user_agent`, `expire_at`. Hand that `id` to the
player:

```
https://cdn.streamlike.com/play?med_id=MEDIA_ID&sltoken=TOKEN_ID
```

Related player parameters: `sltoken_duration` (validity in seconds), `sltoken_ip_ids` and
`sltoken_referrer_ids` (comma-separated ids of the authorized IP groups or referrers).

Issue the token **per playback request**, from your backend, after your own authorization check.
Never ship an API key to the client so it can mint its own.

### Detecting a restricted media before showing a broken player

`/ws/media` and `/ws/playlist` return, in `metadata.global`:

| Flag | Meaning |
| --- | --- |
| `is_tokenized` | Needs a valid `sltoken` |
| `has_password` | The player will prompt |
| `is_secured` | Restricted by IP or referrer |

A useful rule, the one the JS SDK's playlist player applies:

- tokenized without password → a plain player URL cannot play it. Hide it, or show its cover with a
  message,
- tokenized with password → embed it normally, the player prompts,
- secured by IP or referrer → embed it normally: whether it plays depends on the viewer, not on
  you. Only show a notice if playback actually fails.

To know for sure, probe the player URL with a `HEAD` request: `/play` answers `404` when access
does not pass, and allows cross-origin reads. Treat only that `404` as a failure — a network
error, a CORS rejection or a `5xx` is inconclusive, and hiding a media on an inconclusive probe
removes content that would have played.

## Protecting the platform side

**Webservices.** Calls are checked against a list of authorized server IPs, configured in the back
office under Security → Webservices security. A wildcard (`*`) disables the check for the services
that allow it — convenient, and a standing invitation to bandwidth theft. `vote` cannot be
wildcarded at all, and `manifest` requires whitelisting.

**`company_id` is a secret.** It addresses your entire catalog through the webservices. Keep it
server side; a front end should call your backend, which calls the webservices.

**API keys** carry the rights of the user who created them. Store them like database passwords,
never in a mobile bundle or front-end bundle, rotate through `/me/keys`, and give integrations
their own dedicated user account so revoking one does not lock out a person.

## Domains and addresses to allow through a firewall

Corporate networks that block by default need these open, all over HTTPS:

| Purpose | Allow |
| --- | --- |
| Playback (VOD and live) | `*.streamlike.com`, `*.streamlive.cloud`, `*.theoplayer.com`, `storage.googleapis.com` |
| Back office and API | `bo.streamlike.com`, `api.streamlike.com` |
| CDN delivery | `cdn.streamlike.com` — served by Google's CDN, whose IP ranges change; follow Google's published `goog.json` list rather than pinning addresses |
| Websites | `www.streamlike.com`, `www.mediatech.fr`, `*.streamlike.tv` |

Ask your Streamlike contact for the current list before writing firewall rules: it is revised as
infrastructure moves.

## File integrity

Every manifest carries SHA-256 signatures of the encoded files. Keeping the original signature
gives you a way to prove a file has not been altered since ingestion.
