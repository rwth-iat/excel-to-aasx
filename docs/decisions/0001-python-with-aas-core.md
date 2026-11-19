# 0001. Build in Python on aas-core3.1

- **Status:** accepted
- **Date:** 2026-11-19
- **Relates to:** whole project

## Context

The reference implementation (AASX Package Explorer, "Import NAMUR SMTs") is C#. We need the same import behaviour, later AASX → AsciiDoc and a web editor with live PDF preview. The team's other AAS tools (aaspect) are Python, and the Claude Code hooks and review setup assume Python.

AAS metamodel V3.1 is a hard requirement: the example package uses the namespace `https://admin-shell.io/aas/3/1`. Checked on 2026-11-19 with the example package:

- `basyx-python-sdk` 2.2.0 fails to read it (`TypeError: issubclass() arg 1 must be a class`).
- `aas-core3.1` 1.0.0 reads it and verifies it (it reports 128 constraint violations in the example, mostly invalid idShorts and empty language strings, which is useful in itself).

`aas-core3.1` is generated from the same meta-model as `AasCore.Aas3_1`, the C# library the Package Explorer uses. Type and attribute names map one to one, which makes porting the C# logic direct.

## Decision

Python ≥ 3.12 with `uv`. AAS model, XML (de)serialisation and verification come from `aas-core3.1`. Excel is read with `openpyxl`. XML from uploads is parsed through `defusedxml`. The AASX (OPC) package layer is our own small adapter on `zipfile`, because `aas-core3.1` has no packaging.

## Consequences

**Good:** One language across the team's AAS tools. A direct mapping from the Package Explorer C# code. V3.1 works today. Built-in metamodel verification.

**Bad:** We do not run the reference implementation, so we have to port it and keep up with its changes by hand. We own the OPC packaging code (relationships, content types, supplementary files), which basyx would have provided. `aas-core3.1` has no "parent" pointers or convenience helpers like the C# `Extensions`; we write the few we need.

**Neutral:** `aas-core3.1` types (`aas_core3_1.types`) are third-party, so by the layer rules they stay out of `domain`. See the open question in `CLAUDE.md`.

## Alternatives considered

| Option | Why not |
|---|---|
| C#/.NET reusing Package Explorer libraries | Different toolchain from the team's other projects; hooks and review setup would need rework. |
| Python on `basyx-python-sdk` | Cannot read the V3.1 example package (checked with 2.2.0). |
| Drive the Package Explorer headless | Desktop app, Windows-centric; no stable CLI for the table import. |

## Revisit when

`basyx-python-sdk` ships V3.1 support and AASX packaging becomes a burden, or `aas-core3.1` stops keeping up with metamodel releases (V3.2).
