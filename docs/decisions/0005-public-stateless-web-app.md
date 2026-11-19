# 0005. The web app is public, anonymous and stores nothing

- **Status:** accepted
- **Date:** 2026-11-19
- **Relates to:** the planned web editor, ADR 0004

## Context

The command line covers Excel → AASX → AsciiDoc → PDF. The web app should offer the same to people on a public website, Overleaf-style for the AsciiDoc part. The user decided (2026-11-19): it is hosted publicly, needs no user accounts, and keeps no data. You upload an Excel file, download the AASX, convert it to AsciiDoc and edit it with a preview; coming back later to the same work is not needed. A link to aaspect may come later.

## Decision

The web app has no accounts and no database. Each browser session works on its own temporary data on the server, which is deleted after the session ends or a short idle time. Results leave only as downloads (AASX, AsciiDoc folder as ZIP, PDF). Every upload and every edited document is untrusted input from an anonymous user.

## Consequences

**Good:** No personal data, no login flow, no backups or retention rules to handle. Deleting temp data is the whole data-protection story.

**Bad:** Anyone can call every endpoint, so the server must protect itself: upload size limits (already in the readers), a cap on concurrent and per-client PDF builds, timeouts, and cleanup of temp data. PDF builds are the expensive part (about 7 s and up to 1 GB RAM each, ADR 0004). A closed tab loses unsaved work unless the user downloaded it.

**Neutral:** Work in progress can still be kept in the user's own browser (local storage) without the server storing anything. That choice is left to the editor design.

## Alternatives considered

| Option | Why not |
|---|---|
| Accounts with saved projects | Not wanted; adds personal data, storage and login work. |
| Local-only tool | The user wants it hosted. |

## Revisit when

Users ask to keep projects across sessions, or the aaspect integration needs a shared store.
