# 0008. An imported submodel gets an IDTA-style starter document as AsciiDoc submodel

- **Status:** accepted
- **Date:** 2026-11-19
- **Relates to:** ADR 0002, 0006, `docs/spec/asciidoc-export.md`

## Context

An AASX made from an Excel workbook holds only the data submodel. The web editor needs an AsciiDoc document to edit, and Package Explorer has no generator for one: people write it by hand or copy it from a template package. The users are expected to write IDTA submodel template specifications (the institute maintains the IDTA AsciiDoc specs; IDTA publishes newer SMT specs as AsciiDoc/Antora). The user chose (2026-11-19) an IDTA frame plus generated content.

## Decision

`add-document` adds a Package Explorer AsciiDoc submodel (semanticId `.../functions/asciidoc/1/0`) to the package, so the same document works in Package Explorer and in our export. It contains:

- **Frame** (template `templates/idta/`): theme, fonts, CSS and cover graphics taken from the example package; cover page, Imprint, General chapters, the table-format annex and Bibliography following IDTA's published SMT documents, with placeholder text marked `*TODO:*`.
- **Generated:** a chapter "Submodel <idShort>" with a UML overview, the table of the submodel and one table per collection, as `generate-uml` / `generate-tables` references into the data submodel.

The data submodel itself is not changed. The new submodel is written into the existing package; all other package parts are copied unchanged.

## Consequences

**Good:** The first PDF already looks like an IDTA specification with complete tables; users write only the prose. Round trip with Package Explorer.

**Bad:** Every starter document carries IDTA branding (logo, cover, publisher address), which is wrong for non-IDTA use; a neutral template would be a second template folder. The IDTA logo and cover graphics are IDTA's; they are fine for IDTA specification work, not for other purposes. Placeholder text can be left in by mistake. A package then has two submodels, so `diff` needs `--submodel` to pick the data one.

## Alternatives considered

| Option | Why not |
|---|---|
| Plain generated document | Users would have to rebuild the IDTA layout (theme and fonts are files, not editor content). |
| Copy the example document | Starts every document with NAMUR flowmeter text. |
| Generate only an `.adoc` file, not a submodel | Breaks the round trip with Package Explorer and needs a second rendering path. |

## Revisit when

Someone needs documents that are not IDTA specifications, or IDTA changes its SMT document structure.
