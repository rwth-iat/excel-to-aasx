# AASX → AsciiDoc export: rules

Ports the Package Explorer "Export SMT as AsciiDoc" function: `src/AasxPluginExportTable/Smt/ExportSmt.cs` on branch `MIHO/2607_SmtTabsNamur` (commit `71c8f12`). Markers as in `namur-import.md`: **[PE]** reproduces the C# code, **[ours]** differs on purpose, **[example]** was inferred from the example PDF where the source we have is older than the build that made it.

## 1. Input

1. **[PE]** The document is a submodel with semanticId `http://admin-shell.io/aasx-package-explorer/functions/asciidoc/1/0`. **[ours]** The CLI picks the first such submodel, or the one named with `--submodel`.
2. **[PE]** Each element's *function* is the last part of its semanticId after `.../functions/asciidoc/`, version `1/0`: `textblock`, `coverpage`, `heading1`–`heading4`, `imagefile`, `tablerecord`, `generate-tables`, `generate-uml`, `generate-enum-table`, `iterate-list`, `target-model`. Key types are ignored.
3. **[PE]** Options come from the extension `ExportSmt.Args` (JSON). **[ours]** Read leniently: trailing commas allowed and `"true"` counts as true, because Newtonsoft does the same and the example relies on it.

## 2. Order

1. **[PE]** Elements are written in pre-order (parent before children). Elements without a function are skipped, but their children are not.
2. **[PE]** An `iterate-list` collection is repeated once per entry of `itemsA`. In each round, `%ITEMA%`, `%ITEMB%`, … are replaced in idShorts, descriptions, Blob contents and reference keys.
3. **[example]** Any `itemsX` letter works. The example PDF fills `%ITEMC%`, which the ported C# commit does not support yet.
4. **[ours]** All placeholders in a text are replaced. PE replaces only one when a text holds both `%ITEMA%` and `%ITEMB%`.

## 3. Output per function

| Function | Element | Output |
|---|---|---|
| `coverpage`, `textblock` | Blob | Its text, as is. **[PE]** |
| `heading1`–`heading4` | Blob | A blank line, then `==` … `=====` plus the text. **[PE]** |
| `imagefile` | Blob, File | The data as a file next to the document; unless `noLink`, a blank line, `image::<file>[id="<idShort>", <attrs>]` and a blank line. `attrs`: `width="<w:.1f>%"`, `title="<description>"`. **[PE]** |
| `generate-tables` | ReferenceElement | A table of the referenced element's direct children, inlined after `// Table generated from <keys>` (section 5). **[PE]** |
| `generate-uml` | ReferenceElement | **[ours, for now]** A comment and a warning. Step 3c. |
| `generate-enum-table` | ReferenceElement | **[ours, for now]** A comment and a warning. |
| `tablerecord` | Blob | Nothing written. Its JSON replaces the table preset for all later tables. **[PE]** |
| `target-model` | — | Nothing written. **[PE]** |

## 4. Files

1. **[PE]** Blob data that is ASCII-only and not a text content type (`text/plain`, `text/markdown`, …, `application/json`) is base64 and gets decoded. The extension is guessed from the first bytes (`.jpg`, `.gif`, `.png`, fallback `.png`); text content types get `.txt`.
2. **[PE]** File elements use the package part they point to and keep its extension. **[ours]** Paths outside the package (URLs) are never fetched; they are reported as "no image data found".
3. **[PE]** The file name is the idShort with characters outside `[a-zA-Z0-9_-]` turned into `_`. `_dot_` in the idShort marks the extension: `my-theme_dot_yml` → `my-theme.yml`. `fileName` in the args overrides it.
4. **[ours]** `fileName` is untrusted: only its last path segment is kept, and characters outside `[a-zA-Z0-9_.-]` become `_` (a warning says so). The writer also refuses any name that would land outside the output folder.
5. **[PE]** The document is named after the submodel idShort (filtered to `[a-zA-Z0-9_]`), `.adoc`.
6. **[ours]** Line endings are LF everywhere. Blob texts with CRLF are converted.

## 5. Tables

Port of `ExportTableProcessor.ExportAsciiDoc` and `ItemProcessor` (`domain/document/tables/`).

1. **[PE]** The reference keys are followed from the package: submodel id, then idShorts; inside a list, a key that is a number is an index. A target that cannot be found is an error.
2. **[PE]** The preset is "Submodel template spec - AsciiDoc" from Package Explorer's `options.json`, extracted as data into `tables/builtin.py`. A `tablerecord` blob replaces it.
3. **[PE]** Each template cell is filled in two steps. First, `%tag%` placeholders get values; unknown tags become the preset's `FailText` (empty). Second, `%name=value%` directives from the cell and its table, row and column headers set formatting: `bg`, `fg`, `font`, `width`, `colspan`, `trim`, `table-bg`.
4. **[PE]** ConceptDescriptions are found by semanticId without version (`MatchCdNoVersion` is on in the shipped options; `domain/ids.py` ports `IriIrdiRemoveVersion`). Without this, the example's definitions would be missing.
5. **[PE]** `columnWidths` in the args override the preset widths; `|` in values is escaped.
6. **[ours]** Only `depth: 1` is supported (all 25 tables of the example use it). Other depths write depth 1 and give a warning; Package Explorer would add a table per nested container.
7. **[ours]** Values from the package go into table cells with only `|` escaped, as in Package Explorer. AsciiDoc markup in a value (for example `pass:[...]`) is interpreted when the document is compiled. Compile in secure mode (CLAUDE.md hard rules).

## 6. Untrusted content in the output

The package decides what lands in the output folder. The example ships `extended.rb` (Ruby), `.bat` and `.ps1` scripts, and the Package Explorer compile command loads `-r ./extended.rb`. Exporting only writes these files. Anything that compiles the document (step 4, the web editor) must never load or run code from the package. See the hard rules in `CLAUDE.md`.

## Check against the example


`excel-to-aasx adoc examples/*.aasx -o out/doc` writes the document, its 25 tables and 18 files with no errors; the only warning is the UML diagram. For every table, the set of ECLASS IRDIs equals the one in the matching table of the example PDF, and CD definitions appear as in the PDF. 89 of 96 prose lines are found verbatim in the text of the example PDF; the other 7 differ only by rendering (cross-references become "Figure 2", citations, hyphenation).
