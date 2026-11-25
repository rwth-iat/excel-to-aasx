"""Write the demo workbook offered on the web app's home page.

Every value is invented, so the file can be published under the project license.
Do not paste real vendor data or ECLASS definitions in here: those carry their own terms.

    uv run python tools/make_demo_workbook.py
"""

import datetime
from pathlib import Path

from openpyxl import Workbook

TARGET = (
    Path(__file__).parent.parent
    / "src/excel_to_aasx/adapters/web/static/examples/demo-level-sensor.xlsx"
)
BASE = "https://example.com/excel-to-aasx/demo/"
HEADERS = [
    "SME.idShort", "SME.semanticId", "SME.displayName@en", "SME.displayName@de",
    "CD.idShort", "CD.preferredName@en", "CD.preferredName@de",
    "CD.definition@en", "CD.definition@de", "CD.unit",
    "SME.elementName", "Property.valueType", "SME.multiplicity",
]  # fmt: skip

# (idShort, English name, German name, English definition, German definition,
#  unit, element, valueType, multiplicity)
Row = tuple[str, str, str, str, str, str, str, str, str]

BLOCKS: list[tuple[str, str, str, str, list[Row]]] = [
    ("DemoLevelSensor", "Submodel", "", "Invented technical data of a radar level sensor, for trying out excel-to-aasx. Not a real product.", [
        ("General", "general", "Allgemein", "section with identification data of the device", "Abschnitt mit Identifikationsdaten des Geräts", "", "SMC", "", "One"),
        ("MeasuringRange", "measuring range", "Messbereich", "section with the limits of the measurement", "Abschnitt mit den Grenzen der Messung", "", "SMC", "", "One"),
        ("Electrical", "electrical data", "Elektrische Daten", "section with supply and output data", "Abschnitt mit Versorgungs- und Ausgangsdaten", "", "SMC", "", "ZeroToOne"),
        ("Documents", "documents", "Dokumente", "section with documents supplied with the device", "Abschnitt mit den mitgelieferten Dokumenten", "", "SMC", "", "ZeroToOne"),
    ]),
    ("General", "SMC", "General", "Identification data of the device", [
        ("ManufacturerName", "manufacturer name", "Herstellername", "name of the company that makes the device", "Name des Unternehmens, das das Gerät herstellt", "", "Property", "xs:string", "One"),
        ("ProductDesignation", "product designation", "Produktbezeichnung", "short text that names the product", "kurzer Text, der das Produkt benennt", "", "MLP", "", "One"),
        ("SerialNumber", "serial number", "Seriennummer", "number that identifies one device", "Nummer, die ein einzelnes Gerät kennzeichnet", "", "Property", "xs:string", "ZeroToOne"),
        ("YearOfConstruction", "year of construction", "Baujahr", "year in which the device was made", "Jahr, in dem das Gerät hergestellt wurde", "", "Property", "xs:int", "ZeroToOne"),
    ]),
    ("MeasuringRange", "SMC", "MeasuringRange", "Limits of the measurement", [
        ("MinimumDistance", "minimum measuring distance", "minimaler Messabstand", "smallest distance the device measures", "kleinster Abstand, den das Gerät misst", "m", "Property", "xs:double", "One"),
        ("MaximumDistance", "maximum measuring distance", "maximaler Messabstand", "largest distance the device measures", "größter Abstand, den das Gerät misst", "m", "Property", "xs:double", "One"),
        ("Accuracy", "accuracy", "Messgenauigkeit", "largest deviation of the measured from the true distance", "größte Abweichung des gemessenen vom wahren Abstand", "mm", "Property", "xs:double", "One"),
        ("ProcessTemperature", "process temperature", "Prozesstemperatur", "temperature range of the medium the device works in", "Temperaturbereich des Mediums, in dem das Gerät arbeitet", "°C", "Range", "xs:double", "ZeroToOne"),
    ]),
    ("Electrical", "SMC", "Electrical", "Supply and output data", [
        ("SupplyVoltage", "supply voltage", "Versorgungsspannung", "voltage the device needs to work", "Spannung, die das Gerät zum Betrieb braucht", "V", "Property", "xs:double", "One"),
        ("OutputSignal", "output signal", "Ausgangssignal", "kind of signal the device sends", "Art des Signals, das das Gerät sendet", "", "Property", "xs:string", "One"),
        ("DigitalCommunication", "digital communication", "digitale Kommunikation", "whether the device sends values over a digital protocol", "ob das Gerät Werte über ein digitales Protokoll sendet", "", "Property", "xs:boolean", "ZeroToOne"),
    ]),
    ("Documents", "SMC", "Documents", "Documents supplied with the device", [
        ("DataSheet", "data sheet", "Datenblatt", "document with the technical data of the device", "Dokument mit den technischen Daten des Geräts", "", "File", "", "ZeroToOne"),
        ("OperatingManual", "operating manual", "Betriebsanleitung", "document that explains how to install and use the device", "Dokument, das Einbau und Gebrauch des Geräts erklärt", "", "File", "", "ZeroToOne"),
    ]),
]  # fmt: skip

README = [
    "Demo workbook for excel-to-aasx",
    "",
    "Every value in this workbook is invented. It shows the layout of the 'Import NAMUR SMTs'",
    "table import of the AASX Package Explorer; see docs/spec/namur-import.md.",
    "",
    "The first tab holds blocks of 6 top rows (idShort, Class, semanticId, Parent, Explanation,",
    "column headers) followed by one row per element. Blocks are separated by empty rows.",
]


def _semantic_id(id_short: str) -> str:
    return f"{BASE}{id_short}/1/0"


def build() -> Workbook:
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.title = "Import"
    parent = BLOCKS[0][0]
    for id_short, kind, parent_name, explanation, rows in BLOCKS:
        sheet.append(["idShort:", id_short])
        sheet.append(["Class:", kind])
        sheet.append(["semanticId:", _semantic_id(id_short)])
        sheet.append(["Parent:", parent if parent_name else None])
        sheet.append(["Explanation:", explanation])
        sheet.append(HEADERS)
        for name, pref_en, pref_de, def_en, def_de, unit, element, value_type, card in rows:
            display_de = pref_de[:1].upper() + pref_de[1:]
            sheet.append([
                name, _semantic_id(name), pref_en, display_de, name, pref_en, display_de,
                def_en, def_de, unit or None, element, value_type or None, card,
            ])  # fmt: skip
        for _ in range(3):
            sheet.append([])
    notes = book.create_sheet("README")
    for line in README:
        notes.append([line])
    book.properties.creator = "excel-to-aasx"
    book.properties.lastModifiedBy = "excel-to-aasx"
    fixed = datetime.datetime(2026, 1, 1)
    book.properties.created = fixed
    book.properties.modified = fixed
    return book


if __name__ == "__main__":
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    build().save(TARGET)
    print(TARGET)
