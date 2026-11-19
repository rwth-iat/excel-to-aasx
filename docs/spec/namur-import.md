# NAMUR SMT Excel import: rules

The contract for the Excel → AASX import (ADR 0002). Source of truth for behaviour is the AASX Package Explorer, branch `MIHO/2607_SmtTabsNamur`, commit `71c8f12`:

- preset "Import NAMUR SMTs" in `src/AasxPluginExportTable/AasxPluginExportTable.options.json`
- `src/AasxPluginExportTable/Table/ImportPopulateByTable.cs` (block scan, element creation)
- `src/AasxPluginExportTable/Table/ImportCellMatcher.cs` (cell → field)
- `src/AasxPluginExportTable/Table/ImportTableExcelProvider.cs` (cell access)

Rules marked **[PE]** reproduce the C# code. Rules marked **[ours]** differ on purpose. Rules marked **[guess]** cover the 13-column layout, which has no published C# code yet.

## 1. Workbook

1. **[PE]** Every worksheet is scanned. Sheets with no matching block (e.g. `README`) produce nothing.
2. **[PE]** Cell (row r, col c) is read from A1 on, as text. An empty cell is `""`.
3. **[ours]** Numbers are written as text without a trailing `.0` when they are whole (ClosedXML's `ToString()` does the same in an invariant culture). Formulas: the cached value is used.
4. **[PE]** A row is *empty* when all of its first 13 cells are empty. Columns after the 13th (the example has a copy of the semanticId in column N) are ignored.

## 2. Blocks

A block is 6 *top* rows followed by *body* rows.

| Top row | Column A (must equal exactly) | Column B |
|---|---|---|
| 1 | `idShort:` | parent idShort |
| 2 | `Class:` | parent element type: `Submodel`, `SMC`/`SubmodelElementCollection`, `SML`/`SubmodelElementList` |
| 3 | `semanticId:` | parent semanticId |
| 4 | `Parent:` | name of the parent's parent (used for the hierarchy lookup) |
| 5 | `Explanation:` | parent description |
| 6 | anything | column headers (not checked) |

1. **[PE]** Scan from the top. Skip empty rows. A row starts a block when rows 1–5 match column A above. Other non-matching rows are skipped one by one.
2. **[PE]** Body rows follow the 6 top rows and end at the first empty row. The 3 empty rows between blocks in the example are not required.
3. **[PE]** Scanning stops after 100 empty rows in a row.

## 3. Body columns

| Col | Header | Goes to |
|---|---|---|
| A | `SME.idShort` | element idShort |
| B | `SME.semanticId` | element semanticId, and the id of its ConceptDescription |
| C | `SME.displayName@en` | **[guess]** element displayName, language `en` |
| D | `SME.displayName@de` | **[guess]** element displayName, language `de` |
| E | `CD.idShort` | CD idShort |
| F, G | `CD.preferredName@en`, `@de` | CD IEC 61360 preferredName |
| H, I | `CD.definition@en`, `@de` | CD IEC 61360 definition |
| J | `CD.unit` | CD IEC 61360 unit |
| K | `SME.elementName` | element type |
| L | `Property.valueType` | value type (Property only) |
| M | `SME.multiplicity` | `SMT/Cardinality` qualifier |

## 4. Parent element (top rows)

1. **[PE]** `Class: Submodel`: idShort, semanticId, description and qualifiers are copied onto the target submodel. Body rows go to the submodel root.
2. **[PE]** `Class: SMC`: first try the *hierarchy lookup*. Among all collections in the submodel (any depth), find the first one where
   - its parent's idShort is a case-insensitive substring of the `Parent:` cell (or of an alias recorded by an earlier lookup), **and**
   - its idShort equals (case-insensitive) one of the parts of the top idShort split at `,` `;` `|`, **or** its semanticId matches the top semanticId.

   If found, body rows go into that collection, and the top's semanticId and description are **dropped**. The `Parent:` value is recorded as an alias of the found collection's parent. If not found, a new collection with the top's data is appended to the submodel root.
3. **[PE]** The lookup only searches collections (SMC). A block for an `SML` always creates a new list at the root.
4. **[PE]** Any other `Class:` value: the block is skipped.

## 5. Body rows → SubmodelElements

1. **[PE]** `SME.elementName` accepts the full type name or the abbreviation (`Prop`, `MLP`, `SMC`, `SML`, `File`, `Blob`, `Range`, `ReferenceElement`, …). Also accepted: `[SMC]`, `SMC / x`.
2. **[PE]** The element gets idShort, semanticId, and the `SMT/Cardinality` qualifier (`valueType xs:string`).
3. **[PE]** Cardinality: `One` by default. `ZeroToOne` for `0..1`, `[0..1]`, `ZeroToOne`; `ZeroToMany` for `0..*`, `[0..*]`, `ZeroToMany`; `OneToMany` for `1..*`, `[1..*]`, `OneToMany`. Any other text, including empty, gives `One`.
4. **[PE]** Property valueType: the cell text, optionally in `[...]`, parsed as an XSD type name (`xs:string`, `xs:float`, …, exact case). Anything unparseable becomes `xs:string`. `n/a` or an element-type name is ignored.
5. **[ours]** An unparseable valueType that looks like a near miss (`xs: date`, `xs:Boolean`) is still `xs:string` (as in PE), but reported as a warning.
6. **[ours]** Property, File and MLP get no value (PE writes `""`, and for MLP a language string `en: ""`, which fails metamodel verification).
7. **[PE]** semanticId: one key, type `GlobalReference`, value = cell text, reference type `ExternalReference`.

## 6. Body rows → ConceptDescriptions

1. **[PE]** The CD is handled *before* the element. If a CD with the row's semanticId already exists, it is reused and the row's CD columns are ignored (first row wins). In the example, 129 rows share 99 semanticIds. The id comparison ignores the `#NNN` version suffix only when the plugin option `MatchCdNoVersion` is set (default: exact match). We use exact match.
2. **[PE]** A new CD gets id = semanticId, idShort = `CD.idShort` or, if empty, `SME.idShort`, and one IEC 61360 embedded data specification with preferredName, definition and unit.
3. **[PE]** A row with an empty semanticId gets a generated id from the template `www.example.com/ids/cd/DDDD_DDDD_DDDD_DDDD`, used for both the element and the CD. **[ours]** The digits are derived from a hash of the submodel id and the element path, so repeated imports give the same ids. PE uses random digits.
4. **[ours]** PE seeds every CD with a preferredName `en: ""` before adding the cells, which gives a duplicate `en` entry. We do not.
5. **[ours]** PE creates the CD even when the element row then fails (unknown `SME.elementName`), leaving an orphan CD. We report the row as an error and create neither.

## 7. Validation (all **[ours]**, warnings unless noted)

- idShort not matching `^[a-zA-Z][a-zA-Z0-9_-]*[a-zA-Z0-9_]+$` (the example has `installation instructions`, `pressure drop`, `type of output`). Imported as is, like PE; the AASX then fails verification.
- idShort not unique among siblings. **Error.**
- `SME.elementName` unknown. **Error**, row skipped.
- The full output is run through `aas_core3_1.verification`; findings are reported, not fixed.

## Open questions

1. Columns C/D: is `SME.displayName@xx` really the element's displayName? Needs a raw 13-column import from the Package Explorer.
2. `Explanation:` → description: PE parses `text@lang` pairs (`(.*?)@(\w+)`), and text without `@` becomes `en`. A cell with an `@` in plain text (an email address) is split wrongly. Do we reproduce that?
3. The target submodel's id: PE imports into an existing submodel. We need a rule for creating one (proposal: the CLI takes `--submodel-id`, default derived from the semanticId).
