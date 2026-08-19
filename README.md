# Streamlike integration skill

A skill for AI coding assistants — Claude Code, Claude.ai and anything else that reads
`SKILL.md` — that teaches them how to build on Streamlike: which door to use for what,
authentication, catalog reading, playback, security, analytics and feeds.

It is written for the developers and teams who integrate Streamlike into their own products. It
contains nothing confidential: everything here is public documentation, public OpenAPI
descriptions, public SDKs, and behaviour verified against the production platform.

## Contents

```
SKILL.md              What the assistant loads first: pick the door, prerequisites, rules
examples.md           Calls that run as-is against the public demonstration catalog
references/           One file per surface — webservices, API, player, JS SDK, playback,
                      security, analytics, feeds
cookbook/             End-to-end recipes: mobile feed app, WebTV, server-side ingest
scripts/              fetch-openapi.sh, openapi_lookup.py — query a 2.5 MB API description
                      without reading it whole
```

## Using it

**With Claude Code.** Copy the folder into your project or your home skills directory:

```bash
cp -r integration-skill ~/.claude/skills/streamlike-integration
# or, per project:
cp -r integration-skill .claude/skills/streamlike-integration
```

The assistant loads it on its own when a task mentions Streamlike medias, playlists, the player or
the API.

**Anywhere else.** The files are plain Markdown. Point your assistant at `SKILL.md`, or read them
yourself — they work as documentation.

Nothing here needs an account to be read, and `examples.md` needs none to be run.

**On the command line**, the scripts stand alone:

```bash
scripts/fetch-openapi.sh
scripts/openapi_lookup.py search subtitle
scripts/openapi_lookup.py show /medias/{media_id}/audio-tracks
```

## Before you start building

An integration needs a Streamlike account, its `company_id`, API access enabled, an API key, and —
for a few webservices — your server's IP whitelisted. Accounts are opened by Streamlike; there is
no self-service signup. Ask your account manager. `SKILL.md` lists exactly what to request.

## Keeping it current

The OpenAPI descriptions are fetched live, so endpoint details never go stale. The prose does:
re-check the player parameter table and the platform changelogs after a release. Both changelogs
are in the descriptions themselves, under `info.description`.

## Official resources

- REST API description — https://api.streamlike.com/openapi.json
- Webservices description — https://cdn.streamlike.com/openapi.json
- SDKs — https://github.com/Streamlike (`js-streamlike-sdk`, `php-api-sdk`, `php-ws-sdk`)
- Technical blog, articles for developers — https://www.streamlike.fr/blog/
- Back office — https://bo.streamlike.com
