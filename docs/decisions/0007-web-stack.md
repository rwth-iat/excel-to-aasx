# 0007. FastAPI backend, plain JavaScript frontend, vendored libraries

- **Status:** accepted
- **Date:** 2026-11-19
- **Relates to:** ADR 0001, 0005, 0006

## Context

The web app wraps the existing use-cases (import, AsciiDoc export, PDF build) for anonymous users (ADR 0005) and needs an editor with an HTML preview in the browser (ADR 0006). The team's other web projects use FastAPI with plain HTML/CSS/JS (ES modules, no build step, no CDN).

## Decision

- **Backend:** FastAPI as a new adapter `adapters/web`, wired in `main.py` like the CLI. Use-cases arrive as callables. Each session gets a temporary *workspace* folder with a random 128-bit id, deleted after an idle timeout.
- **Frontend:** static HTML/CSS and ES modules, no framework and no build step for our own code. Strict CSP (`script-src 'self'`).
- **Libraries:** CodeMirror 6 (editor) and asciidoctor.js (preview), pinned and vendored into `static/vendor/`. CodeMirror 6 ships as many ES packages, so it is bundled once into a single file by `tools/vendor.sh`; the bundle is committed, together with the versions used.

## Consequences

**Good:** Same patterns as the team's other projects; no Node toolchain to run the app; no third-party requests from users' browsers.

**Bad:** Vendored files (~1.5 MB) live in the repo and must be updated by hand. Updating CodeMirror needs Node once, for the bundle. No AsciiDoc syntax highlighting is available for CodeMirror 6; the editor shows plain text with line numbers, search and undo.

## Alternatives considered

| Option | Why not |
|---|---|
| React/Vue SPA with a build pipeline | More moving parts than one editor page needs. |
| Load libraries from a CDN | Third-party requests and a weaker CSP; other team projects avoid it. |
| Monaco editor | Several MB, needs its own loader. |

## Revisit when

The frontend grows beyond one editor page, or a maintained AsciiDoc mode for CodeMirror 6 appears.
