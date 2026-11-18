# SPDX-License-Identifier: CERN-OHL-S-2.0
# Copyright (C) 2026 Cesar Kastli
"""Generates the bill of materials from the schematic: hardware/bom.csv and a
printable hardware/bom.pdf (A4, Spanish, with checkboxes).

    python3 hardware/tools/gen_bom.py

gen_schematic.py runs it at the end, so the BOM follows every schematic change.
Needs kicad-cli (KiCad 10) and Google Chrome (prints the HTML to PDF). Parts
are grouped by reference prefix. FOOTPRINT_TEXT turns footprints into the
words a shop understands. NOTES adds buyer notes per part. EXTRAS lists what
the schematic doesn't carry. Text is Spanish because the PDF is a document.
"""
import csv
import datetime
import html
import re
import subprocess
import tempfile
from pathlib import Path

HW = Path(__file__).resolve().parents[1]
SCH = HW / "kicad" / "pots-in-a-box.kicad_sch"
CSV_OUT = HW / "bom.csv"
PDF_OUT = HW / "bom.pdf"
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# (title, reference prefixes), in print order
GROUPS = [
    ("Resistencias y presets", ("R", "RV")),
    ("Capacitores", ("C",)),
    ("Diodos y LED", ("D",)),
    ("Transistores", ("Q",)),
    ("Circuitos integrados", ("U",)),
    ("Cristales", ("Y",)),
    ("Relés", ("K",)),
    ("Fusibles reseteables (PTC)", ("F",)),
    ("Conectores", ("J", "SW")),
]

# footprint name (without library) -> shop words; first regex that matches wins
FOOTPRINT_TEXT = [
    (r"R_Axial_DIN0207", "¼ W axial, paso 10,16 mm"),
    (r"R_Axial_DIN0309", "½ W axial, paso 12,7 mm"),
    (r"R_Axial_DIN0414", "1 W axial, paso 15,24 mm"),
    (r"R_Axial_Power_L25", "5 W axial, paso 27,94 mm"),
    (r"Potentiometer_Bourns_3296W", "Preset multivuelta 3296W"),
    (r"CP_Radial_D(\d+)\.0mm_P(\d+\.\d+)mm", "Electrolítico radial Ø{0} mm, paso {1} mm"),
    (r"C_Disc_.*_P5\.00mm", "Cerámico disco, paso 5 mm"),
    (r"C_Rect_L18\.0mm_W8\.0mm_P15", "Film (poliéster) 18 × 8 mm, paso 15 mm"),
    (r"D_DO-41", "DO-41 axial"),
    (r"D_DO-35", "DO-35 axial"),
    (r"D_DO-15", "DO-15 axial"),
    (r"LED_D3\.0mm", "LED 3 mm"),
    (r"TO-220-3_Vertical", "TO-220, vertical"),
    (r"TO-126-3_Vertical", "TO-126, vertical"),
    (r"TO-92_Inline_Wide", "TO-92, patas abiertas a 2,54 mm"),
    (r"TO-92_Inline", "TO-92"),
    (r"DIP-28_W7\.62mm_Socket", "DIP-28 angosto, con zócalo"),
    (r"DIP-(\d+)_W7\.62mm", "DIP-{0}"),
    (r"Crystal_HC49-4H", "Cristal HC-49/S (bajo)"),
    (r"Relay_DPDT_Omron_G5V-2", "Relé DPDT bobina 12 V, huella G5V-2"),
    (r"Fuse_Bourns_MF-RG", "PTC radial (tipo Bourns MF-RG)"),
    (r"BarrelJack_Horizontal", "Jack de alimentación (barril), horizontal"),
    (r"TerminalBlock.*-(\d+)-5\.08", "Bornera {0} polos, paso 5,08 mm"),
    (r"IDC-Header_2x03", "Conector IDC 2 × 3 con traba"),
    (r"PinHeader_1x0(\d)_P2\.54mm", "Tira de pines 1 × {0}, paso 2,54 mm"),
    (r"RJ12_Amphenol", "Jack modular RJ12 (6P), horizontal"),
]

# buyer notes, keyed by the first reference of a BOM line
NOTES = {
    "R20": "R_BRIDGE del puente H.",
    "D102": "Valor pendiente de la prueba de banco: P6KE82CA / 100CA / 120CA según el riel de ring.",
    "Q101": "Pasaje del limitador de lazo.",
    "U2": "Con zócalo DIP-28.",
    "K3": "2 de ring (uno por línea) + 1 de unión.",
    "J1": "Jack para la fuente de 12 V.",
    "SW1": "Conector a la llave del panel.",
    "J2": "Conecta el módulo elevador (V_LINE).",
    "J3": "Programación del ATmega.",
    "J4": "Puerto serie / programación.",
}

# not in the schematic: (qty, part, note)
EXTRAS = [
    (2, "Zócalo DIP-18", "MT8870 (U102, U202). Opcional."),
    (2, "Zócalo DIP-8", "IR2104 (U3, U4). Opcional."),
    (1, "Zócalo DIP-16", "ULN2003A (U5). Opcional."),
    (2, "Zócalo DIP-4", "PC817 (U101, U201). Opcional."),
    (1, "Módulo elevador ajustable", "Salida a V_LINE, en J2."),
    (1, "Fuente de 12 V, 2 A", "Plug para J1."),
    (1, "Llave AR/US para el panel", "Con cable a SW1."),
    (4, "Tornillos M3 y separadores", "Posición final según el gabinete."),
    (1, "Gabinete", "ABS 150 × 120 × 40 mm (en evaluación)."),
]

COLS = '<colgroup><col style="width:4%"><col style="width:6%"><col style="width:12%"><col style="width:24%"><col style="width:31%"><col style="width:23%"></colgroup>'

CSS = """
@page { size: A4; margin: 12mm 11mm 14mm; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; font-size: 8.6pt; color: #111; margin: 0; }
header { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1.5pt solid #111; padding-bottom: 4pt; margin-bottom: 6pt; }
h1 { font-size: 15pt; margin: 0; }
.meta { font-size: 8pt; color: #444; text-align: right; }
h2 { font-size: 10pt; margin: 9pt 0 3pt; break-after: avoid; }
h2 .n { font-weight: normal; color: #666; font-size: 8pt; margin-left: 4pt; }
table { table-layout: fixed; width: 100%; border-collapse: collapse; break-inside: auto; }
tr { break-inside: avoid; }
th, td { border: 0.5pt solid #999; padding: 2.2pt 4pt; vertical-align: top; text-align: left; }
th { background: #eee; font-size: 7.6pt; text-transform: uppercase; letter-spacing: .02em; }
td.ck, th.ck { text-align: center; font-size: 10pt; }
td.q, th.q { text-align: right; }
td.v { font-weight: 600; overflow-wrap: anywhere; }
td.refs { font-family: Menlo, Consolas, monospace; font-size: 7.4pt; }
td.note { color: #333; font-size: 7.6pt; }
.summary { font-size: 8pt; margin: 0 0 4pt; color: #333; }
footer { margin-top: 8pt; font-size: 7.4pt; color: #555; }
"""


def export_csv():
    subprocess.run([CLI, "sch", "export", "bom", "-o", str(CSV_OUT),
                    "--fields", "Reference,Value,Footprint,${QUANTITY},Description",
                    "--labels", "Refs,Value,Footprint,Qty,Description",
                    "--group-by", "Value,Footprint", "--ref-range-delimiter", "",
                    "--exclude-dnp", str(SCH)], check=True, capture_output=True)
    with CSV_OUT.open(newline="") as f:
        return list(csv.DictReader(f))


def prefix(ref):
    return re.match(r"[A-Z]+", ref).group()


def ref_key(ref):
    return prefix(ref), int(re.search(r"\d+", ref).group())


def mm(value):
    """'3.50' -> '3,5', '5.00' -> '5' (Spanish decimal comma)."""
    return f"{float(value):g}".replace(".", ",")


def package(footprint):
    name = footprint.split(":")[-1]
    for pat, text in FOOTPRINT_TEXT:
        m = re.search(pat, name)
        if m:
            return text.format(*(mm(g) for g in m.groups()))
    return name  # unknown: print the raw footprint so it gets noticed


def row(cells):
    return "<tr>" + "".join(f'<td class="{c}">{v}</td>' for c, v in cells) + "</tr>"


def render(lines):
    e = html.escape
    groups = {title: [] for title, _ in GROUPS}
    for ln in lines:
        refs = sorted(ln["Refs"].split(","), key=ref_key)
        title = next((t for t, pre in GROUPS if prefix(refs[0]) in pre), None)
        if title is None:
            raise SystemExit(f"gen_bom: no group for {refs[0]}; add its prefix to GROUPS")
        groups[title].append((refs, ln))
    total = sum(int(ln["Qty"]) for ln in lines)
    body = []
    for title, items in groups.items():
        if not items:
            continue
        items.sort(key=lambda it: ref_key(it[0][0]))
        n = sum(int(ln["Qty"]) for _, ln in items)
        body.append(f'<h2>{e(title)} <span class="n">{n} piezas</span></h2><table>{COLS}'
                    '<thead><tr><th class="ck"></th><th class="q">Cant.</th><th>Valor</th><th>Encapsulado</th>'
                    '<th>Referencias</th><th>Notas</th></tr></thead><tbody>')
        for refs, ln in items:
            body.append(row([("ck", "☐"), ("q", ln["Qty"]), ("v", e(ln["Value"])),
                             ("", e(package(ln["Footprint"]))), ("refs", e(", ".join(refs))),
                             ("note", e(NOTES.get(refs[0], "")))]))
        body.append("</tbody></table>")
    extras = "".join(row([("ck", "☐"), ("q", q), ("", e(p)), ("note", e(note))]) for q, p, note in EXTRAS)
    today = datetime.date.today().strftime("%d/%m/%Y")
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>POTS in a box — Lista de materiales</title>
<style>{CSS}</style></head><body>
<header><h1>POTS in a box — Lista de materiales</h1>
<div class="meta">Placa principal, 2 líneas · {today}<br>Generada de hardware/kicad/{SCH.name}</div></header>
<p class="summary">{total} piezas en {len(lines)} renglones. Todas de inserción (THT). Las referencias 1xx son de la línea L1 y las 2xx de la línea L2.</p>
{"".join(body)}
<h2>No incluido en el esquemático (sumar a la compra)</h2>
<table><colgroup><col style="width:4%"><col style="width:6%"><col style="width:36%"><col style="width:54%"></colgroup>
<thead><tr><th class="ck"></th><th class="q">Cant.</th><th>Pieza</th><th>Notas</th></tr></thead><tbody>{extras}</tbody></table>
<footer>Los valores pueden cambiar después de la prueba de banco (docs/prueba-banco.md). Regenerar esta lista desde el esquemático antes de comprar.</footer>
</body></html>"""


def main():
    lines = export_csv()
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "bom.html"
        page.write_text(render(lines))
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--user-data-dir={tmp}/chrome", f"--print-to-pdf={PDF_OUT}", page.as_uri()],
                       check=True, capture_output=True)
    print(f"BOM: {sum(int(ln['Qty']) for ln in lines)} parts in {len(lines)} lines -> {CSV_OUT.name}, {PDF_OUT.name}")


if __name__ == "__main__":
    main()
