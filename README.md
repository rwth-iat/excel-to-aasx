# excel-to-aasx

Converts vendor Excel property sheets (NAMUR SMT import format) into AASX packages
(AAS metamodel V3.1), matching the "Import NAMUR SMTs" table import of the
[AASX Package Explorer](https://github.com/eclipse-aaspe/package-explorer).

Planned: AASX to AsciiDoc rendering, and a web editor with live PDF preview.

## Setup

```bash
uv sync
uv run excel-to-aasx --help
```

## Docs

- Import rules: [`docs/spec/namur-import.md`](docs/spec/namur-import.md)
- Decisions: [`docs/decisions/`](docs/decisions/)
