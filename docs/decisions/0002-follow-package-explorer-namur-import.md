# 0002. Import rules follow the Package Explorer "Import NAMUR SMTs" preset

- **Status:** provisional — pending verification
- **Date:** 2026-11-19
- **Relates to:** Excel → AASX import, ADR 0001, `docs/spec/namur-import.md`

## Context

The workbook README says: import it in the AASX Package Explorer with "Import table .." and the preset "Import NAMUR SMTs". The preset does not exist on the Package Explorer `main` branch. It is on branch `MIHO/2607_SmtTabsNamur`, commit `71c8f12` (2026-10-19), titled "define new import template * update before extending to 13 cols".

That preset has **11** columns. The example workbook has **13**: it adds `SME.displayName@en` and `SME.displayName@de`. Also, the C# matcher for SME fields has no language-tag handling (`displayName@en` would not match), so the 13-column version needs C# changes that are not published. We infer how those two columns behave; we cannot read it.

## Decision

The import reproduces the behaviour of `ImportPopulateByTable` and `ImportCellMatcher` at that commit, with the 13-column layout of the example workbook. Every rule, and every place we knowingly differ, is written down in `docs/spec/namur-import.md`. The spec is the contract; code follows it.

Deliberate differences from the C# code (details in the spec):
- Deterministic ConceptDescription ids instead of random ones when a row has no semanticId.
- No CD preferred-name entry with an empty text for the default language (the C# context seeds one).
- Hard errors for an unknown `SME.elementName` and for invalid idShorts are reported, not skipped silently.

## Consequences

**Good:** One clear reference, and the user's Excel files keep working the same way in both tools.

**Bad:** We inherit the preset's fuzzy parts, notably the "act in hierarchy" lookup that matches parent names by substring. Package Explorer changes on that branch can make us drift. The two display-name columns are a guess until checked against a real 13-column import.

## Alternatives considered

| Option | Why not |
|---|---|
| Design our own clean mapping | Users would get different results from the tool their README names. |
| Port only the 11-column preset | The example workbook would not import. |

## Revisit when

- Someone runs the 13-column import in the Package Explorer (from the author of `MIHO/2607_SmtTabsNamur`, or a published build) and we can diff its raw output against ours.
- That branch is merged to `main` or changes the preset again.
