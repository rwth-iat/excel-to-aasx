# 0009. On a server, PDFs are built by a separate builder service

- **Status:** accepted
- **Date:** 2026-11-19
- **Relates to:** ADR 0004 (supersedes its "a container per build" for the server), ADR 0005

## Context

ADR 0004 builds each PDF in a fresh, locked-down container. That needs access to the Docker daemon, which is root on the host: if the public web app (ADR 0005) is ever compromised, whoever controls it can start containers and owns the machine. The user chose (2026-11-19) a separate builder service.

## Decision

`docker compose` runs two services:

- **app** (web app): no Docker access, non-root, read-only root file system, on a public network and an internal one.
- **builder** (`builder/`): the same pinned `asciidoctor/docker-asciidoctor:1.108.1` image plus a standard-library HTTP server. `POST /build` takes a ZIP of the flat document folder and returns the PDF. It is only on an internal network without internet access, non-root, read-only with a tmpfs, with memory, process and CPU limits, a per-build timeout that kills the whole process group, at most two builds at once, and PlantUML in `SANDBOX` mode (no `!include` of files or URLs).

The app uses the builder when `EXCEL_TO_AASX_BUILDER_URL` is set; otherwise (CLI, development) it keeps the container per build of ADR 0004. Package Explorer themes name fonts as `/documents/<file>`; the builder rewrites that prefix to its build folder.

## Consequences

**Good:** Nobody holds Docker access. A compromised app can only send build jobs; a compromised build cannot reach the internet or the app's data. Builds start faster (about 2 s instead of 7 s: no container start).

**Bad:** Builds share one long-lived container instead of a fresh one each: a build could leave files in `/tmp` for the next (each build gets its own temporary folder, deleted afterwards). Two code paths for PDFs (builder, local container) must stay equivalent; both use the same image, options and extension.

**Neutral:** The builder is internal; it has no authentication. Anything that can reach the internal network can submit builds.

## Alternatives considered

| Option | Why not |
|---|---|
| Docker socket in the app container | Root on the host for the public-facing process. |
| asciidoctor-pdf and Java inside the app image | Builds share the app's container and network access. |

## Revisit when

Builds need stronger isolation from each other (then: a fresh sandbox per build, e.g. gVisor or Firecracker), or the builder must be shared by several apps (then it needs authentication).
