# 0011. The PDF builder renders PlantUML diagrams for the live preview

- **Status:** accepted
- **Date:** 2026-11-25
- **Relates to:** ADR 0005, ADR 0006 (revises its "diagrams are missing until the PDF is built"), ADR 0009

## Context

Every starter document has a UML overview of the submodel (ADR 0008), written as a PlantUML block. The live preview renders AsciiDoc in the browser (ADR 0006), and browsers cannot run PlantUML: it is a Java program that also needs Graphviz. So the preview shows the diagram's source text, and users see the diagram only after building the whole PDF. The user chose (2026-11-25) to render diagrams on the server.

## Decision

The browser sends the text of each PlantUML block to `POST /api/workspaces/{id}/diagram` and shows the SVG that comes back as an `<img>` in the preview. The app accepts exactly one `@startuml … @enduml` diagram (no other PlantUML diagram types, no `newpage`), because `-pipe` renders every diagram in its input (`domain/diagram_source.py`). It passes the text to a **separate diagram service**: the builder image (ADR 0009) run a second time, with PDF builds switched off and a hard limit of 1 CPU and 768 MB for all renders together. PDF builds and diagrams therefore never compete. The builder service has diagrams switched off.

Each render runs the PlantUML jar from the image with:
- `PLANTUML_SECURITY_PROFILE=SANDBOX` on the command line (no `!include` of files or URLs, no environment variables);
- a JVM limited to 1 processor and 256 MB heap;
- at most 10 s of CPU time and 5 MB of SVG (process limits set before PlantUML starts), lower priority (`nice 10`);
- a 15 s timeout, its own empty working folder, at most two renders at once.

Without the services (CLI, development), the app starts a locked-down container per diagram with the same limits, like a PDF build (ADR 0004).

Limits per session (`adapters/web/throttle.py`): one render in flight, at least 2 s between renders, at most 60 s of render time per 10 minutes. The request needs an open workspace, at most 64 KB of text. The browser asks only when a diagram's text has changed and typing has paused for 1.5 s, one request at a time with 2 s between them, and retries once after "busy". Per-IP limits belong to the reverse proxy (`docs/deployment.md`).

## Consequences

**Good:**
- The preview shows the UML overview without a PDF build: about 1 s per diagram in the diagram service (1 CPU), about 6 s with a container per diagram (measured 2026-11-25).
- Nothing leaves our servers: no public PlantUML or Kroki service sees the document (ADR 0005).
- The diagram comes from the same PlantUML version that builds the PDF.

**Bad:**
- Typing inside a diagram now makes the server work, about one JVM start per pause. This is what ADR 0006 avoided. When all slots are taken, the diagram stays as text until a retry succeeds, instead of queueing.
- One more endpoint takes untrusted input into Java and Graphviz. Its protection is the sandbox profile, the one-diagram check, the service's isolation (no network, read-only, limits) and the per-render limits.
- Per-session limits do not stop someone who opens many sessions; each needs an upload, and the proxy has to limit per IP. A determined attacker can still keep the diagram service busy and so deny previews to others, but no longer slow down PDF builds or the app.
- One more container to run, from the same image. The PlantUML jar path and JVM arguments are kept in two places (app and builder); a test keeps them equal.

**Neutral:** The SVG is shown through `<img>`, so scripts or links inside it never run, even before the preview iframe's sandbox applies.

## Alternatives considered

| Option | Why not |
|---|---|
| Public PlantUML or Kroki server | Sends user documents to a third party (ADR 0005). |
| PlantUML compiled to run in the browser (TeaVM, CheerpJ) | Experimental, several MB of download, and Graphviz has to run as WebAssembly too. |
| Our own diagram drawing (e.g. Mermaid) for generated diagrams only | Edits to the PlantUML text would not show, and the preview would differ from the PDF. |

## Revisit when

- Diagram renders overload the diagram service; then keep one JVM running (PlantUML `-picoweb`) or cache SVGs on the server.
- A PlantUML build that runs in the browser becomes stable and small enough.
