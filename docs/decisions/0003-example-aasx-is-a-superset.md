# 0003. Test against the example AASX as a superset, not for equality

- **Status:** provisional — pending verification
- **Date:** 2026-11-19
- **Relates to:** ADR 0002, `examples/`, the `diff` CLI command

## Context

The example pair is not "input and raw output". Checked on 2026-11-19:

- The AASX has two submodels. One holds the AsciiDoc spec document (`.../functions/asciidoc/1/0`). The other, `NamurTechnicalDataVariableAreaFlowMeter`, holds the data.
- The data submodel has 149 elements; the workbook defines 129 rows. Extra elements were added (e.g. `GeneralInformation` with a `CompanyLogo` file), values are filled in (e.g. `ManufacturerName = KROHNE`), and the submodel was renamed (workbook: `NAMUR_SMT_FloatTypeFowMeter`).
- The imported tree sits below `TechnicalPropertyAreas/ECLASS_ADV_V17/`, not at the submodel root.
- All 98 distinct workbook idShorts and all 99 distinct semanticIds (ignoring the `#NNN` version suffix) do occur in it.

So the example is the import plus later manual work. Equality can never hold.

## Decision

The golden test checks that every element our import produces exists in the reference, at the same path below a mount point (`TechnicalPropertyAreas/ECLASS_ADV_V17` for the example), with the same element type and semanticId (version suffix ignored). Extra elements, values and later edits in the reference are allowed. ConceptDescriptions are checked the same way, by id.

## Consequences

**Good:** The test is useful now, with the only reference we have.

**Bad:** A superset check cannot catch elements we produce that the import would not have produced in that place, if the reference happens to contain them. Fields changed by hand later (cardinality, display names, semanticId versions) show up as differences we must judge by eye.

## Alternatives considered

| Option | Why not |
|---|---|
| Exact equality against the example | Fails by design: the example was edited after import. |
| No golden test until a raw import exists | Leaves the converter untested against real data for an unknown time. |

## Revisit when

We get a raw Package Explorer import of the example workbook (see ADR 0002). Then switch the golden test to equality against that file and keep this check as a second test.
