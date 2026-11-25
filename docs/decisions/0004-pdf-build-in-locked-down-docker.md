# 0004. Build PDFs with asciidoctor-pdf in a pinned, locked-down Docker image

- **Status:** accepted
- **Date:** 2026-11-19
- **Relates to:** AASX → PDF (`pdf` command), the planned web editor, `docs/spec/asciidoc-export.md`. On a server, ADR 0009 replaces the container per build with a builder service.

## Context

The PDF must look like the IDTA spec documents that Package Explorer users build. Package Explorer itself calls `asciidoctor-pdf` in the official `asciidoctor/docker-asciidoctor` image, with the package's theme (`my-theme.yml`) and `-r ./extended.rb`, a Ruby file that also comes from the package.

In the web editor, both the document and the package come from users. AsciiDoc can read files (`include::`, images) and asciidoctor loads any Ruby given with `-r`. Running either with full rights means remote code execution and reading server files.

Checked on 2026-11-19 with the example package: image `1.108.1` (Asciidoctor 2.0.26, asciidoctor-pdf 2.3.27, asciidoctor-diagram with PlantUML, Java and Graphviz) builds 39 A4 pages, the same count as the reference PDF, with 99.5 % of the words in the same order. The rest is the missing UML figure. The package's `extended.rb` is the upstream asciidoctor-pdf "numbered paragraphs" example.

## Decision

`asciidoctor-pdf` runs in `asciidoctor/docker-asciidoctor:1.108.1` (pinned in `main.py`) with `--safe-mode secure`, no network, no capabilities, `no-new-privileges`, a read-only root file system, memory, process and CPU limits, the caller's uid, and a timeout after which the container is killed. Only the document folder is mounted. Package-supplied Ruby is never loaded; we ship our own copy of the upstream numbered-paragraphs extension (MIT). The package theme is used, because a YAML theme cannot run code.

## Consequences

**Good:** Same toolchain as Package Explorer, so the output matches the reference. Untrusted documents cannot read host files (tested with `include::/etc/passwd[]`) or reach the network. No Ruby or Java on the host.

**Bad:** Needs Docker on the machine that builds PDFs, and an image of about 2.3 GB on disk. A container start costs about 1 s of the ~7 s build. Features that need `unsafe` mode or package extensions are not available. A theme can still point at fonts and images inside the folder, which is fine, since everything in the folder came from the same package. Upgrading the image can change the layout, so it is a deliberate change.

**Neutral:** The web editor will need a faster preview path (asciidoctor.js in the browser, or a warm container); that is its own decision.

## Alternatives considered

| Option | Why not |
|---|---|
| Install Ruby, asciidoctor-pdf and Java on the host | Runs untrusted documents without isolation; drifts from the reference toolchain. |
| Run the package's `extended.rb` as Package Explorer does | Arbitrary code execution from an upload. |
| Unpinned `latest` image | Layout could change between builds without anyone deciding it. |

## Revisit when

The web editor needs previews faster than a container start, or a newer image is needed for a feature.
