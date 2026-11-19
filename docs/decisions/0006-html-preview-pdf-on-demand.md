# 0006. Live preview in HTML in the browser; the PDF is built on request

- **Status:** accepted
- **Date:** 2026-11-19
- **Relates to:** ADR 0004, ADR 0005, the web editor

## Context

The editor should feel like Overleaf: edit AsciiDoc on the left, see the result on the right. A real PDF build takes about 7 s and up to 1 GB of memory (ADR 0004), and on a public, anonymous site (ADR 0005) anyone can trigger it. Rebuilding on every pause in typing would be slow for the user and easy to abuse. The user chose (2026-11-19) an HTML live preview plus a PDF built on click.

## Decision

While typing, the browser renders the AsciiDoc to HTML with asciidoctor.js; the server does no work. A "Build PDF" button sends the current text to the server, which builds the exact PDF (ADR 0004) for checking and download. The HTML preview is shown in a sandboxed iframe with scripts disabled, because AsciiDoc can carry raw HTML.

## Consequences

**Good:** Instant preview; no server load while typing; PDF builds happen only on purpose, so a simple limit on concurrent builds protects the server.

**Bad:** The preview is not the PDF: page breaks, the cover page, the IDTA theme, numbered paragraphs and the PlantUML diagrams (which need Java on the server) look different or are missing until the PDF is built. Two renderers (asciidoctor.js and Asciidoctor in Ruby) may disagree on edge cases.

**Neutral:** The HTML preview uses the package's images from the server, read-only.

## Alternatives considered

| Option | Why not |
|---|---|
| Rebuild the PDF on every pause | ~7 s delay per change and an easy way to overload a public server. |
| Both, switchable | Most work; can be added later if the HTML preview proves too far from the PDF. |

## Revisit when

Users report that the preview differs too much from the PDF, or builds get fast enough (warm container, caching) to run on pause.
