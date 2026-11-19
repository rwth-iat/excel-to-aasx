# excel-to-aasx — working rules

Converts vendor Excel property sheets into AASX packages (AAS metamodel V3.1). The reference implementation is the Excel importer in the [AASX Package Explorer](https://github.com/eclipse-aaspe/package-explorer) (C#): match its output before inventing behaviour.

Planned later:
1. AASX → AsciiDoc rendering of a submodel specification (like the IDTA spec PDF in `examples/`).
2. A web editor, similar to Overleaf: edit the AsciiDoc, see a live PDF preview.

Past decisions: `docs/decisions/`. Stack (ADR 0001): Python ≥ 3.12, `uv`, `aas-core3.1` for the AAS model, `openpyxl`, `defusedxml`.
Import rules: `docs/spec/namur-import.md` is the contract (ADR 0002). AsciiDoc export rules: `docs/spec/asciidoc-export.md`. Code follows the specs; change the spec first.

```bash
uv sync                                    # install, including dev tools
uv run pytest -q                           # tests
uv run pyright                             # types
uv run excel-to-aasx import examples/*.xlsx -o out/import.aasx
uv run excel-to-aasx diff out/import.aasx examples/*.aasx   # superset check (ADR 0003)
uv run excel-to-aasx adoc examples/*.aasx -o out/doc          # AsciiDoc submodel -> folder
uv run excel-to-aasx pdf examples/*.aasx -o out/pdf           # ... plus PDF (needs Docker, ADR 0004)
docker pull asciidoctor/docker-asciidoctor:1.108.1            # once; tests that need it skip without it
```

## Reference material (`examples/`)

| File | What it is |
|---|---|
| `Import_Properties_Schwebe_2_added_Li_v09_HOMI_Gerd-1.xlsx` | Input. Sheets `Import` (properties) and `README` (format notes). |
| `Namur_SMT_VariableAreaFlowMeters_v09_2nd_delivery (1).aasx` | Expected output of the import (AAS V3.1 XML, plus supplementary files). |
| `AsciiDoc_Namur_SMT_Tech_Data_Variable_Flow_Meter-1.pdf` | Rendered spec (IDTA 02200-1-0). Its AsciiDoc source lives inside the AASX, as the submodel `AsciiDoc_Namur_SMT_Tech_Data_Variable_Flow_Meter` (Package Explorer AsciiDoc function, semanticId `http://admin-shell.io/aasx-package-explorer/functions/asciidoc/1/0`). |

The AASX is not the raw import of the xlsx: it was edited afterwards (ADR 0003). The imported tree sits under `TechnicalPropertyAreas/ECLASS_ADV_V17` of `NamurTechnicalDataVariableAreaFlowMeter`.

These files cannot be regenerated. Never modify or delete them; the `guard` hook blocks `rm` on `*.xlsx`, `*.aasx`, `*.pdf`. Generated output goes to `out/` (gitignored).

## Hard rules

These outrank every other consideration, including "it's just a quick test". The `brick-check` hook blocks on the first three.

1. **Never extract an uploaded ZIP with `extractall`.** AASX and XLSX are ZIPs from untrusted users (zip slip, zip bombs). Read members by name, check resolved path and size.
2. **Never call a process through a shell** (`shell=True`). Pass argument lists.
3. **Asciidoctor never runs in `unsafe` mode.** Edited AsciiDoc is untrusted: `include::` and `image::` must not read server files.
4. **Never load or run code that came from a package.** The example AASX ships `extended.rb`, `.bat` and `.ps1` files, and the Package Explorer compile command loads `-r ./extended.rb`. Compile only with our own extensions and theme.
5. **Uploaded files are untrusted input**, every value inside them too (cell values, idShorts, descriptions, semanticIds, embedded files). Parse XML without external entities. Escape values before they go into AsciiDoc.

## Layers — imports point inward only

```
domain ← ports ← app ← adapters ← main.py
```

All under `src/excel_to_aasx/`.

| Layer | Holds | May import |
|---|---|---|
| `domain` | Pure conversion rules: rows as the converter sees them, row-to-SubmodelElement mapping, idShort rules, document outline. No I/O, no third-party packages. | `domain` |
| `ports` | `Protocol`s only. Zero implementations. | `domain` |
| `app` | Use-cases: convert workbook → AASX, render AASX → AsciiDoc, compile AsciiDoc → PDF. | `domain`, `ports` |
| `adapters/*` | Outside world, one sub-package per concern (`excel`, `aasx`, `asciidoc`, `pdf`, `web`, `cli`). | `domain`, `ports` |
| `config` | Settings, read once at startup. | `domain` |
| `main.py` | Composition root, the **only** module that constructs adapters. | anything |

`app` importing an adapter is always a mistake: what you want is a new method on a port.
An adapter importing a sibling adapter is always a mistake: hoist the shared thing into `domain`, or wire both in `main.py`.

Open question for an early ADR: whether the AAS SDK's model types (e.g. basyx) may cross into `domain`, or `domain` keeps its own types.

## Build in bricks

- **One reason to change per module.** Two unrelated causes means two modules.
- **Name the seam before you write code.** Say which layer this belongs in. Unclear? Resolve the design first.
- **Port before implementation.** Protocol, then use-case, then adapter. The most-likely-to-change piece is written last and stays smallest.
- **Wire in exactly one place**: `src/excel_to_aasx/main.py`. No singletons, no module-level construction.
- **Test at the cheapest layer** that proves the thing. The end-to-end test is: `examples/*.xlsx` in, AASX equivalent to `examples/*.aasx` out.

| Budget | Soft | Hard |
|---|---|---|
| File | 200 LOC | 300 LOC |
| Function | 40 LOC | — |
| Public names per module | 5 | — |
| Modules per package | 8 | — |

Budgets detect design smells, not style violations. The hook reports them; it does not block.

## Working efficiently

- Session start injects a repo map with per-file LOC, the decision index and git state. **Read that before globbing.**
- Grep for symbols, not files. Read the specific function, not the whole module.
- Inspect AASX/XLSX with `unzip -l` / `unzip -p`, not by reading the binary.
- **If understanding a change needs more than three files open at once, the seam is in the wrong place.** Say so instead of pushing through.

## How to ask a question

The person you are asking knows the tools but not necessarily every protocol and standard underneath them (AAS metamodel, OPC packaging, Asciidoctor internals). A question they cannot evaluate is a decision waved through, not made.

- **One decision at a time.** Ask, wait for the answer, then open the next.
- **Problem first.** The real-world situation, what goes wrong if chosen badly, then the options. Never open with a protocol or library name.
- **Say where things stand** in two or three lines before asking.
- **Always offer "not sure — talk me through it".**
- **Affirm what is sound before correcting what is not.**

This applies to ADRs too: an ADR whose Context only makes sense to someone who already knows the answer has failed.

## Before you decide

Non-trivial technical choices get checked against `docs/decisions/` **first**. If new work contradicts an existing ADR, surface the conflict; see the `decision-record` skill.

Decisions marked `provisional` rest on unverified assumptions (how the Package Explorer importer really maps a row, what basyx or Asciidoctor support, how other vendors' sheets look). When you learn the real answer, revisit the ADR; do not quietly build on the guess.

## Git

- Never push to `main`. Work on a feature branch; merge via PR. The `guard` hook blocks force-push, push to main, `reset --hard` and `git clean -f`.
- Commit or push only when the user asks.

## Tooling

| | |
|---|---|
| Skills | `modular-design` · `decision-record` |
| Agents | `code-review-logic-architecture` · `code-review-security` |
| Commands | `/brick-check` (audit structure) · `/adr <topic>` · `/reassess` (decisions vs. reality) |
| Hooks | session start: repo map · before Bash: guard · after Write/Edit: ruff format + fix, brick-check · stop: pyright, pytest · git commit-msg: message rules (install: `ln -s ../../.claude/hooks/commit_msg.py .git/hooks/commit-msg`) |
| Rules config | `.claude/architecture.json`: change limits **there**, nowhere else |
| Check locally | `python .claude/hooks/brick_check.py --all` |

Hooks run with plain `python3` (stdlib only, ≥ 3.10) and use ruff/pyright/pytest from `.venv`; without them installed the format, typecheck and test hooks silently do nothing.

Language: code, comments, ADRs and commit messages in **English**.

## Code comments

- Default to no comment. Well-named functions and variables explain *what* the code does.
- Only comment to explain *why*: non-obvious decisions, workarounds, edge cases, links to specs (IDTA, AAS metamodel, Package Explorer source), surprising behavior.
- Never write comments that restate the code, narrate your changes, or address the reader.
- Don't leave comments about what was removed or changed. That belongs in the commit.
- Keep docstrings for public APIs short: one line summary, then params/returns only if non-obvious.

## Commit messages

Enforced by the git `commit-msg` hook.
- Conventional Commits: `type(scope): summary` (types: feat, fix, refactor, docs, test, chore, perf).
- Summary: imperative mood, max ~50 chars, no trailing period.
- Blank line, then a body wrapped at 72 chars explaining *why* and notable trade-offs. Skip it for trivial changes.
- Describe intent, not a file-by-file list. One logical change per commit.
- No emojis, no "This commit...", no marketing language, no Co-authored-by trailer.

## Pull requests

- Title: same format as a commit subject.
- Body sections, each short: `## Why` (problem or goal, link issues), `## What` (notable changes and trade-offs, grouped by intent), `## Testing` (checklist; say plainly what was not tested).
- One logical change per PR. No emojis, no "Generated with" footer, no Co-authored-by lines.
