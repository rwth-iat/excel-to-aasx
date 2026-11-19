# Picking a seam in this project

A seam is where you can replace one side without the other noticing. Put them where change is *likely*, not everywhere — a port that will only ever have one implementation and no test double is just noise.

## Candidate seams, and why

None of these exist yet. They follow from the three planned pipelines (Excel → AASX, AASX → AsciiDoc, AsciiDoc → PDF in a live-preview web editor). Names are proposals. Confirm (or reject) each one when the first feature that needs it is built, and record the choice as an ADR.

| Port (proposed) | Separates | Why it will actually move |
|---|---|---|
| `SheetReader` | Use-cases from `.xlsx` mechanics (openpyxl) | Excel layouts differ per vendor/delivery; the reader library is a technology choice. Tests should feed rows, not files. |
| `PackageStore` | Use-cases from AASX read/write (basyx, OPC packaging, supplementary files) | AASX is a ZIP with relationships and embedded files; metamodel version (V3.1 today) will move. **Likely the highest-risk seam.** |
| `DocumentRenderer` | Use-cases from AsciiDoc text generation | Layout of the spec document is still unknown and will change often. |
| `PdfCompiler` | Use-cases from Asciidoctor-PDF (external process or service) | Slow, external, needs fonts/themes; tests must not need it. Untrusted input crosses here. |

## Name ports for what the caller needs

Name a port for **what the caller needs**, not for the technology behind it. `PackageStore`, not `BasyxWrapper`: if the AAS SDK changes, the name still holds and `app` does not change.

## Test: is this a real seam?

Ask: **"Can I write a fake for this that makes a test meaningfully cheaper?"**

- `SheetReader` → a fake hands the mapping in-memory rows; no fixture workbooks needed for most tests. Real seam.
- `PdfCompiler` → a fake turns a multi-second Asciidoctor run into a no-op. Real seam.
- A hypothetical `IdShortSanitizer` port → a fake buys nothing. Not a seam; just call the function.

## When NOT to add a port

- One implementation, no test benefit, no plausible second implementation → call the code directly.
- The "abstraction" is a rename of the thing behind it (a wrapper with openpyxl's exact methods) → that is a wrapper, not a boundary.

Over-porting carries its own maintenance cost. Be sceptical of every port beyond the ones above.
