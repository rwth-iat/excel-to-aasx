# 0010. Keep the reference files out of git; tests use an invented demo workbook

- **Status:** accepted
- **Date:** 2026-11-25
- **Relates to:** ADR 0003, ADR 0008, `tests/`, `tools/make_demo_workbook.py`, `NOTICE`

## Context

The project was built against three files from a vendor delivery: the input workbook, the edited AASX and the rendered PDF (ADR 0003). None of them may be published:

- The workbook carries a company sensitivity label, and every printed page has the footer "RESTRICTED". There is no license anywhere in it, and its file properties name two people.
- Its concept definitions look ECLASS-derived, and ECLASS data has its own license terms.
- The AASX contains a vendor's logo and product images.

The repository is meant to be shared, and the web app is public (ADR 0005). A file that is in git history once leaks with every clone, and deleting it in a later commit does not remove it from history.

## Decision

The reference files are not in git, in any commit, and no test reads them. Tests, the quick start and the home page use `demo-level-sensor.xlsx`, which `tools/make_demo_workbook.py` writes with invented values, so it falls under the project license. Tests that need a reference package (the `diff` superset check) build one in code (`tests/test_cli_diff.py`). Developers who have the vendor files may keep them in `examples/`, which `.gitignore` excludes, for manual checks with `excel-to-aasx diff`.

History was rewritten on 2026-11-25 to remove the files from every branch.

## Consequences

**Good:** The repository and the web app can be made public. Every test runs the same everywhere, with nothing skipped, and nothing third-party ships in the image. Anyone can try the converter with the demo workbook, which imports with no errors and no warnings.

**Bad:**
- No automated test checks our output against real vendor data any more. The comparison with the reference AASX (ADR 0003) and the 39-page PDF word-for-word check are gone; a regression that only real data shows goes unnoticed until someone runs `diff` by hand.
- The demo workbook is small (5 blocks, 17 elements). Warnings, invalid idShorts and the hierarchy lookup are covered only by unit tests on hand-written rows, not by a real sheet.
- The export tests now cover only the starter document we generate, not a hand-edited AsciiDoc submodel like the vendor's (iterate-lists, per-section UML, custom column widths).

**Neutral:** All commit hashes changed with the rewrite. Any older clone still holds the files and must be deleted.

## Alternatives considered

| Option | Why not |
|---|---|
| Keep the files, only stop tracking them | The old commits still contain them; any clone can recover them. |
| Keep the tests, skip them without the files | Tests that run only on one machine are not a safety net; the files must not reach production or CI either. |
| A private test-data repository or CI secret | Same: the files would still be needed outside the owner's control. |
| Anonymise the vendor files | Still derived from RESTRICTED material; the right to publish stays unclear. |

## Revisit when

- A workbook and AASX are available that may be published (for example an IDTA template or one we build ourselves with the Package Explorer); then add them as test fixtures and restore the comparison test.
- A real-data regression slips through that the demo tests missed; then grow the demo workbook or the unit tests to cover it.
