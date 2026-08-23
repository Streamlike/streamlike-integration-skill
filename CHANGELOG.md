# Changelog

Version numbers follow [semantic versioning](https://semver.org): the major digit moves when a
recipe or a rule that integrators depend on changes meaning, the minor when surface is added, the
patch for corrections that change nothing you would have written differently.

The same version is published to both distributions — the Claude skill and the Gemini gem — from
the same source.

## 1.0.0 — 2026-08-23

First numbered release. The content had already been published; this is the point where it starts
being versioned, so an integrator can tell which state of the platform they are reading about.

- covers the three public surfaces: webservices, REST API, hosted player, plus the JS SDK,
  playback, security, analytics and feeds,
- carries the API surface as of API 5.38 and webservices 5.20 — the per-track audio endpoints and
  the `multiple_audio` playlist filter are described and flagged as not yet in production,
- adds a Gemini gem distribution alongside the Claude skill, built from the same files.
